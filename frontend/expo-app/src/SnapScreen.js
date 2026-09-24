import React, { useRef, useState } from "react";
import { Image, ScrollView, StyleSheet, Text, View } from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import * as ImagePicker from "expo-image-picker";
import { identify, poi } from "./api";
import { C } from "./theme";
import { Button, Card, Chip, ErrorBox, Loading } from "./ui";
import POIView from "./POIView";

export default function SnapScreen({ onAR, goExplore }) {
  const [perm, askPerm] = useCameraPermissions();
  const camRef = useRef(null);
  const [photo, setPhoto] = useState(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [activePoi, setActivePoi] = useState(null);
  const [err, setErr] = useState(null);

  function resetShot() {
    setPhoto(null);
    setResult(null);
    setActivePoi(null);
    setErr(null);
  }
  async function snap() {
    setBusy(true);
    try {
      const shot = await camRef.current.takePictureAsync({ quality: 0.9 });
      setPhoto(shot.uri);
      setResult(null);
      setActivePoi(null);
      setErr(null);
    } catch (e) {
      setErr("Could not take a photo: " + e.message);
    } finally {
      setBusy(false);
    }
  }
  async function upload() {
    const picked = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      quality: 0.9,
    });
    if (!picked.canceled) {
      setPhoto(picked.assets[0].uri);
      setResult(null);
      setActivePoi(null);
      setErr(null);
    }
  }
  async function runIdentify() {
    setBusy(true);
    setErr(null);
    try {
      const r = await identify(photo);
      setResult(r);
      if (r.status === "recognised" && r.matched) setActivePoi(r.matched.poi_id);
      else setActivePoi(null);
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function chooseCandidate(poiId) {
    setBusy(true);
    try {
      const info = await poi(poiId);
      setResult({ status: "recognised", matched: { poi_id: poiId, name: info.poi.name } });
      setActivePoi(poiId);
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={{ flex: 1 }}>
      {busy ? (
        <View style={s.center}>
          <Loading label="Identifying…" />
        </View>
      ) : photo ? (
        <ScrollView contentContainerStyle={{ padding: 14, paddingBottom: 30 }}>
          <Image source={{ uri: photo }} style={s.preview} />
          <View style={s.actions}>
            <Button label="Retake" onPress={resetShot} />
            <Button label="Identify" variant="primary" onPress={runIdentify} />
          </View>
          {err ? <ErrorBox message={err} /> : null}
          {result && result.status === "candidates" ? (
            <Card>
              <Text style={s.h2}>Which one did you mean?</Text>
              <Text style={[s.sub, { marginBottom: 10 }]}>
                That photo didn't clear the confidence bar ({Math.round(result.confidence_score * 100)}%) — tap the match.
              </Text>
              {result.candidates.map((c) => (
                <Button
                  key={c.poi_id}
                  style={{ marginBottom: 8 }}
                  label={`${c.name}   ${Math.round(c.score * 100)}%`}
                  onPress={() => chooseCandidate(c.poi_id)}
                />
              ))}
            </Card>
          ) : result && result.status === "not_recognised" ? (
            <Card>
              <Text style={s.h2}>Not recognised</Text>
              <Text style={[s.sub, { marginVertical: 8 }]}>
                No match was confident enough — I won't guess. Try a clearer angle, or search the catalogue.
              </Text>
              <Button label="Browse catalogue" variant="accent" onPress={goExplore} />
            </Card>
          ) : null}
          {activePoi && result && result.matched ? (
            <POIView poiId={activePoi} onAR={onAR} title={result.matched.name || ""} />
          ) : null}
        </ScrollView>
      ) : (
        <View style={{ flex: 1 }}>
          {perm && perm.granted ? (
            <CameraView ref={camRef} style={s.camera} facing="back" />
          ) : (
            <View style={[s.center, s.camera]}>
              <Text style={s.h2}>Camera needed</Text>
              <Text style={[s.sub, { textAlign: "center", marginVertical: 10 }]}>
                LensGuide recognises landmarks, dishes and signs through your camera.
              </Text>
              <Button label="Allow camera" variant="primary" onPress={() => askPerm()} />
            </View>
          )}
          <View style={s.actions}>
            <Button label="Upload" onPress={upload} />
            <Button label="Snap" variant="primary" onPress={snap} />
          </View>
        </View>
      )}
    </View>
  );
}

const s = StyleSheet.create({
  camera: { flex: 1, width: "100%" },
  preview: { width: "100%", aspectRatio: 3 / 4, borderRadius: 16, backgroundColor: "#000" },
  actions: { flexDirection: "row", gap: 10, marginVertical: 14 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: 20 },
  h2: { color: C.text, fontSize: 18, fontWeight: "800" },
  sub: { color: C.muted, fontSize: 13, lineHeight: 19 },
});