import React, { useRef, useState } from "react";
import { Image, ScrollView, StyleSheet, Text, View } from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import * as ImagePicker from "expo-image-picker";
import { translateImage } from "./api";
import { C } from "./theme";
import { Button, Card, Chip, ErrorBox, Loading } from "./ui";

export default function TranslateScreen() {
  const [perm, askPerm] = useCameraPermissions();
  const camRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [photo, setPhoto] = useState(null);
  const [result, setResult] = useState(null);
  const [err, setErr] = useState(null);

  async function snap() {
    const shot = await camRef.current.takePictureAsync({ quality: 0.9 });
    setPhoto(shot.uri);
    setResult(null);
    setErr(null);
  }
  async function pick() {
    const p = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      quality: 0.9,
    });
    if (!p.canceled) {
      setPhoto(p.assets[0].uri);
      setResult(null);
      setErr(null);
    }
  }
  async function run() {
    setBusy(true);
    setErr(null);
    try {
      setResult(await translateImage(photo));
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={{ padding: 14, paddingBottom: 30 }}>
      <Text style={s.h2}>Sign &amp; menu translation</Text>
      <Text style={[s.sub, { marginTop: 2, marginBottom: 12 }]}>
        Point at a sign or menu; output to English (en-IN).
      </Text>

      {busy ? (
        <Loading label="Reading and translating…" />
      ) : photo ? (
        <>
          <Image source={{ uri: photo }} style={s.preview} />
          <View style={s.actions}>
            <Button
              label="Retake"
              onPress={() => {
                setPhoto(null);
                setResult(null);
                setErr(null);
              }}
            />
            <Button label="Translate" variant="primary" onPress={run} />
          </View>
          {err ? <ErrorBox message={err} /> : null}
          {result ? (
            <Card>
              {result.ocr_text ? <Text style={s.ocr}>"{result.ocr_text}"</Text> : null}
              <Text style={[s.translation, { marginVertical: 8 }]}>{result.translation}</Text>
              <View style={s.flexRow}>
                <Chip text={result.source_language} />
                <Chip text="→" />
                <Chip text={result.target_language} />
                <Chip text={result.confidence} tone={result.confidence === "high" ? "good" : "mid"} />
                {result.fallback === "dataset_reference" ? <Chip text="offline dataset" /> : null}
              </View>
              {result.reference ? (
                <View style={[s.block, { marginTop: 10 }]}>
                  <Text style={s.muted}>Reference translation (eval scorer):</Text>
                  <Text style={s.ref}>{result.reference.reference_translation}</Text>
                  <View style={s.flexRow}>
                    <Chip text={result.matches_reference ? "matches" : "differs"} tone={result.matches_reference ? "good" : "mid"} />
                    <Chip text={result.reference.kind} />
                    {result.reference.is_safety_critical ? <Chip text="⚠ safety-critical" /> : null}
                  </View>
                </View>
              ) : null}
            </Card>
          ) : null}
        </>
      ) : (
        <>
          {perm && perm.granted ? (
            <CameraView ref={camRef} style={s.camera} facing="back" />
          ) : (
            <View style={[s.camera, s.center]}>
              <Text style={s.h2}>Camera needed</Text>
              <Button label="Allow camera" variant="primary" onPress={() => askPerm()} />
            </View>
          )}
          <View style={s.actions}>
            <Button label="From gallery" onPress={pick} />
            <Button label="Snap a sign" variant="primary" onPress={snap} />
          </View>
        </>
      )}
    </ScrollView>
  );
}

const s = StyleSheet.create({
  camera: { width: "100%", aspectRatio: 3 / 4, borderRadius: 16, backgroundColor: "#000", overflow: "hidden" },
  center: { alignItems: "center", justifyContent: "center", padding: 20, gap: 12 },
  preview: { width: "100%", aspectRatio: 3 / 4, borderRadius: 16, backgroundColor: "#000" },
  actions: { flexDirection: "row", gap: 10, marginVertical: 14 },
  h2: { color: C.text, fontSize: 19, fontWeight: "800" },
  sub: { color: C.muted, fontSize: 13, lineHeight: 19 },
  ocr: { color: C.muted, fontSize: 13, fontStyle: "italic" },
  translation: { color: C.text, fontSize: 20, fontWeight: "800" },
  flexRow: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  block: { gap: 6 },
  muted: { color: C.muted, fontSize: 12 },
  ref: { color: C.text, fontSize: 15, fontWeight: "600" },
});