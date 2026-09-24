import React from "react";
import {
  ActivityIndicator,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { C } from "./theme";

export function Button({ label, onPress, variant = "ghost", disabled, style }) {
  const bg =
    variant === "primary" ? C.accent : variant === "accent" ? C.good : C.panel;
  const color =
    variant === "primary" ? "#00131a" : variant === "accent" ? "#00131a" : C.text;
  return (
    <TouchableOpacity
      style={[s.btn, { backgroundColor: bg }, disabled && s.btnDisabled, style]}
      onPress={onPress}
      disabled={disabled}>
      <Text style={[s.btnText, { color }]}>{label}</Text>
    </TouchableOpacity>
  );
}

export function Chip({ text, tone = "normal" }) {
  const col = tone === "good" ? C.good : tone === "mid" ? C.mid : C.text;
  return (
    <View style={[s.chip, { borderColor: col }]}>
      <Text style={[s.chipText, { color: col }]}>{text}</Text>
    </View>
  );
}

export function Loading({ label = "Working…" }) {
  return (
    <View style={s.loading}>
      <ActivityIndicator color={C.accent} />
      <Text style={s.loadingText}>{label}</Text>
    </View>
  );
}

export function ErrorBox({ message }) {
  return (
    <View style={s.card}>
      <Text style={{ color: C.bad, fontSize: 14 }}>{message}</Text>
    </View>
  );
}

export function Card({ children }) {
  return <View style={s.card}>{children}</View>;
}

const s = StyleSheet.create({
  btn: {
    borderRadius: 12,
    paddingHorizontal: 18,
    paddingVertical: 13,
    minHeight: 48,
    alignItems: "center",
    justifyContent: "center",
  },
  btnDisabled: { opacity: 0.4 },
  btnText: { fontSize: 15, fontWeight: "700" },
  chip: {
    alignSelf: "flex-start",
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 3,
  },
  chipText: { fontSize: 11, fontWeight: "700" },
  loading: { alignItems: "center", paddingVertical: 28, gap: 10 },
  loadingText: { color: C.muted, fontSize: 14 },
  card: {
    backgroundColor: C.card,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: C.line,
    padding: 14,
    marginBottom: 12,
  },
});