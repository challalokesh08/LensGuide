"""Contract tests for the LM Studio-first provider implementation.

Covers the real lensguide/llm.py behavior: primary -> fallback provider chain,
structured LLMError mapping, in-memory response caching, the 3-language gate,
and the /api/identify + /api/translate HTTP contracts.

Run:  python -m pytest tests/test_llm_fallback.py -v
"""
import io
import json
import os
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib import error

from lensguide import llm
from lensguide.app import app


class LLMFallbackTests(unittest.TestCase):
    def setUp(self):
        self.original_interval = llm._MIN_INTERVAL
        self.original_last_call = llm._last_llm_call
        llm._MIN_INTERVAL = 0
        llm._last_llm_call = 0
        llm._CACHE.clear()

    def tearDown(self):
        llm._MIN_INTERVAL = self.original_interval
        llm._last_llm_call = self.original_last_call

    def test_primary_rate_limit_uses_configured_fallback(self):
        """A 429 from the primary provider falls through to the configured fallback."""
        env = {
            "LLM_PROVIDER": "gemini",
            "LLM_FALLBACK_PROVIDER": "openai",
            "GEMINI_API_KEY": "gemini-test-key",
            "OPENAI_API_KEY": "openai-test-key",
        }
        fallback = json.dumps(
            {"translation": "Gate opens at 6 AM", "source_language": "en", "confidence": "high"}
        )
        messages = [{"role": "user", "content": "translate something"}]
        with patch.dict(os.environ, env, clear=False), patch.object(
            llm,
            "_gemini_call",
            side_effect=llm.LLMError(
                "quota", status=429, provider="gemini", code="rate_limited"
            ),
        ), patch.object(llm, "_openai_call", return_value=fallback) as fallback_call:
            result = llm._llm(messages)

        self.assertEqual(result, json.loads(fallback))
        fallback_call.assert_called_once()

    def test_rate_limit_is_preserved_when_no_fallback_succeeds(self):
        """With no fallback configured, the structured 429 propagates to the caller."""
        env = {
            "LLM_PROVIDER": "gemini",
            "LLM_FALLBACK_PROVIDER": "",
            "GEMINI_API_KEY": "gemini-test-key",
        }
        with patch.dict(os.environ, env, clear=False), patch.object(
            llm,
            "_gemini_call",
            side_effect=llm.LLMError(
                "quota", status=429, provider="gemini", code="rate_limited"
            ),
        ):
            with self.assertRaises(llm.LLMError) as raised:
                llm._llm([{"role": "user", "content": "translate"}])

        self.assertEqual(raised.exception.status, 429)
        self.assertEqual(raised.exception.code, "rate_limited")

    def test_translation_cache_prevents_repeated_provider_calls(self):
        """In-memory cache keys on the message list; a repeat call skips the provider."""
        env = {"LLM_PROVIDER": "mock", "LLM_FALLBACK_PROVIDER": ""}
        expected = {"translation": "Hello", "source_language": "fr", "confidence": "high"}
        with patch.dict(os.environ, env, clear=False), patch.object(
            llm, "_mock_llm", return_value=json.dumps(expected)
        ) as call:
            first = llm.translate_text("Bonjour", source="auto", target="en-IN")
            second = llm.translate_text("Bonjour", source="auto", target="en-IN")

        self.assertEqual(first, expected)
        self.assertEqual(second, expected)
        self.assertEqual(call.call_count, 1)

    def test_invalid_provider_credentials_are_actionable(self):
        """An HTTP 401 from a provider surfaces as a structured, actionable error."""
        http_error = error.HTTPError(
            "https://example.invalid", 401, "Unauthorized", {}, io.BytesIO(b"{}")
        )
        with patch("lensguide.llm.request.urlopen", side_effect=http_error):
            with self.assertRaises(llm.LLMError) as raised:
                llm._raw_http("https://example.invalid", {}, {}, provider_name="openai")

        self.assertEqual(raised.exception.status, 401)
        self.assertEqual(raised.exception.code, "provider_error")
        self.assertEqual(raised.exception.provider, "openai")
        self.assertIn("401", str(raised.exception))

    def test_combined_error_reports_the_fallback_failure(self):
        """When both providers fail, the raised error names the failing provider."""
        env = {
            "LLM_PROVIDER": "gemini",
            "LLM_FALLBACK_PROVIDER": "openai",
            "GEMINI_API_KEY": "",
            "OPENAI_API_KEY": "bad-test-key",
        }
        with patch.dict(os.environ, env, clear=False), patch.object(
            llm,
            "_openai_call",
            side_effect=llm.LLMError(
                "OpenAI rejected the configured API key or it lacks access.",
                status=503,
                provider="openai",
                code="invalid_credentials",
            ),
        ):
            with self.assertRaises(llm.LLMError) as raised:
                llm._llm([{"role": "user", "content": "translate"}])

        self.assertEqual(raised.exception.provider, "openai")
        self.assertIn("OpenAI rejected", str(raised.exception))

    def test_gemini_call_uses_configured_model(self):
        """_gemini_call builds the request against GEMINI_MODEL and parses JSON."""
        env = {"GEMINI_API_KEY": "gemini-test-key", "GEMINI_MODEL": "gemini-2.5-flash"}
        fake_body = json.dumps(
            {
                "candidates": [
                    {"content": {"parts": [{"text": '```json\n{"translation":"Hello"}\n```'}]}}
                ]
            }
        ).encode()
        with patch.dict(os.environ, env, clear=False), patch(
            "lensguide.llm.request.urlopen", return_value=io.BytesIO(fake_body)
        ) as urlopen:
            result = llm._gemini_call([{"role": "user", "content": "translate to en"}])

        url = urlopen.call_args[0][0].full_url
        self.assertIn("gemini-2.5-flash", url)
        self.assertEqual(result, '{"translation":"Hello"}')

    def test_transport_error_becomes_structured_llm_error(self):
        with patch.dict(os.environ, {"LLM_TIMEOUT_SECONDS": "1"}, clear=False), patch(
            "lensguide.llm.request.urlopen", side_effect=OSError("connection dropped")
        ):
            with self.assertRaises(llm.LLMError) as raised:
                llm._raw_http("https://example.invalid", {}, {}, provider_name="Gemini")

        self.assertEqual(raised.exception.status, 503)
        self.assertEqual(raised.exception.code, "provider_unreachable")


class APIContractTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        llm._CACHE.clear()

    def test_identify_returns_429_contract(self):
        """An LLM rate-limit surfaces as a structured 429 with Retry-After."""
        with patch.object(llm, "image_to_b64", return_value=("b64data", "image/jpeg")), patch.object(
            llm,
            "identify_poi",
            side_effect=llm.LLMError(
                "Gemini quota/rate limit reached.",
                status=429,
                provider="gemini",
                retry_after=30,
                code="rate_limited",
            ),
        ):
            response = self.client.post(
                "/api/identify",
                data={"image": (io.BytesIO(b"image-bytes"), "photo.jpg")},
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 429)
        payload = response.get_json()
        self.assertTrue(payload["quota_exhausted"])
        self.assertEqual(payload["provider"], "gemini")
        self.assertEqual(payload["retry_after"], 30)
        self.assertEqual(payload["code"], "rate_limited")
        self.assertEqual(response.headers["Retry-After"], "30")

    def test_only_three_target_languages_are_accepted(self):
        response = self.client.post(
            "/api/translate",
            json={"text": "Hello", "target": "fr-FR"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Unsupported target language")

    def test_quota_failure_uses_exact_dataset_reference(self):
        db_path = Path(__file__).resolve().parents[1] / "data" / "PS-06.db"
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT source_text_truth, reference_translation FROM menu_sign_images "
            "WHERE reference_translation != '' ORDER BY image_id LIMIT 1"
        ).fetchone()
        conn.close()
        with patch.object(
            llm,
            "translate_text",
            side_effect=llm.LLMError(
                "quota",
                status=429,
                provider="gemini",
                code="rate_limited",
            ),
        ):
            response = self.client.post(
                "/api/translate",
                json={"text": row[0], "target": "en-IN"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["fallback"], "dataset_reference")
        self.assertEqual(payload["translation"], row[1])
        self.assertTrue(payload["matches_reference"])

    def test_image_translation_uses_language_not_landmark_class(self):
        """Image translation feeds the OCR source_language (not label_class) into translate."""
        captured = {}

        def fake_identify(_b64, _mime):
            return {
                "kind": "sign",
                "label_class": "heritage",
                "source_language": "fr",
                "text": "Porte ouverte",
            }

        def fake_translate(_text, source, target):
            captured["source"] = source
            captured["target"] = target
            return {
                "translation": "Gate open",
                "source_language": source,
                "confidence": "high",
            }

        with patch.object(
            llm, "image_to_b64", return_value=("b64data", "image/jpeg")
        ), patch.object(llm, "identify_poi", side_effect=fake_identify), patch.object(
            llm, "translate_text", side_effect=fake_translate
        ):
            response = self.client.post(
                "/api/translate",
                data={"image": (io.BytesIO(b"image-bytes"), "sign.jpg")},
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(captured, {"source": "fr", "target": "en-IN"})


if __name__ == "__main__":
    unittest.main()