import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import { C } from "./theme";

export default function ARView({ scene, onExit }) {
  const [perm, askPerm] = useCameraPermissions();

  return (
    <View style={StyleSheet.absoluteFill}>
      {perm && perm.granted ? (
        <CameraView style={StyleSheet.absoluteFill} facing="back" />
      ) : (
        <View style={[StyleSheet.absoluteFill, s.center]}>
          <Text style={s.h2}>Camera needed for AR</Text>
          <TouchableOpacity style={s.allow} onPress={() => (perm && !perm.granted ? askPerm() : null)}>
            <Text style={s.allowText}>Allow camera</Text>
          </TouchableOpacity>
        </View>
      )}
      <View style={s.bar}>
        <TouchableOpacity onPress={onExit} style={s.exit}>
          <Text style={s.exitText}>✕ Exit AR</Text>
        </TouchableOpacity>
      </View>
      <View style={s.label}>
        <Text style={s.chip}>AR</Text>
        <Text style={s.name}>{scene.name || ""}</Text>
        <Text style={s.fact}>{scene.fact || ""}</Text>
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  center: { alignItems: "center", justifyContent: "center", backgroundColor: "#000", gap: 12 },
  h2: { color: C.text, fontSize: 18, fontWeight: "800" },
  allow: {
    backgroundColor: C.accent,
    borderRadius: 12,
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  allowText: { color: "#00131a", fontWeight: "800" },
  bar: {
    position: "absolute",
    top: 56,
    left: 0,
    right: 0,
    alignItems: "center",
  },
  exit: {
    backgroundColor: "rgba(0,0,0,.6)",
    borderRadius: 999,
    paddingHorizontal: 18,
    paddingVertical: 10,
  },
  exitText: { color: "#fff", fontWeight: "700", fontSize: 15 },
  label: {
    position: "absolute",
    left: 14,
    right: 14,
    bottom: 40,
    backgroundColor: "rgba(4,8,16,.85)",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "rgba(56,225,255,.35)",
    padding: 14,
  },
  chip: {
    color: C.good,
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1,
    marginBottom: 4,
  },
  name: { color: C.accent, fontSize: 18, fontWeight: "800", marginBottom: 4 },
  fact: { color: C.muted, fontSize: 14, lineHeight: 20 },
});