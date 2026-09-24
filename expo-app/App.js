import React, { useState } from "react";
import { SafeAreaView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { StatusBar } from "expo-status-bar";
import SnapScreen from "./src/SnapScreen";
import TranslateScreen from "./src/TranslateScreen";
import ExploreScreen from "./src/ExploreScreen";
import ARView from "./src/ARView";
import { C } from "./src/theme";

const TABS = [
  { key: "snap", label: "Snap" },
  { key: "translate", label: "Translate" },
  { key: "explore", label: "Explore" },
];

export default function App() {
  const [tab, setTab] = useState("snap");
  const [arScene, setArScene] = useState(null);

  return (
    <SafeAreaView style={s.root}>
      <StatusBar style="light" />
      <View style={s.header}>
        <Text style={s.logo}>🪄 LensGuide</Text>
        <View style={s.badge}>
          <Text style={s.badgeText}>GEMINI</Text>
        </View>
      </View>

      <View style={{ flex: 1 }}>
        {tab === "snap" && <SnapScreen onAR={setArScene} goExplore={() => setTab("explore")} />}
        {tab === "translate" && <TranslateScreen />}
        {tab === "explore" && <ExploreScreen onAR={setArScene} />}
      </View>

      <View style={s.tabs}>
        {TABS.map((t) => (
          <TouchableOpacity
            key={t.key}
            style={[s.tab, tab === t.key && s.tabActive]}
            onPress={() => setTab(t.key)}>
            <Text style={[s.tabText, tab === t.key && s.tabTextActive]}>{t.label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {arScene ? <ARView scene={arScene} onExit={() => setArScene(null)} /> : null}
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingTop: 10,
    paddingBottom: 6,
  },
  logo: { color: C.text, fontSize: 18, fontWeight: "800" },
  badge: {
    backgroundColor: "rgba(56,225,255,.15)",
    borderWidth: 1,
    borderColor: C.accent,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 3,
  },
  badgeText: { color: C.accent, fontSize: 11, fontWeight: "800", letterSpacing: 1 },
  tabs: {
    flexDirection: "row",
    borderTopWidth: 1,
    borderTopColor: C.line,
    backgroundColor: C.panel,
    paddingBottom: 6,
  },
  tab: { flex: 1, alignItems: "center", paddingVertical: 12 },
  tabActive: { borderBottomWidth: 2, borderBottomColor: C.accent },
  tabText: { color: C.muted, fontSize: 14 },
  tabTextActive: { color: C.accent, fontWeight: "700" },
});