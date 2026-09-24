import React, { useEffect, useState } from "react";
import { Modal, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { book, nearby, poi } from "./api";
import { C } from "./theme";
import { Button, Card, Chip, ErrorBox, Loading } from "./ui";

export default function POIView({ poiId, onAR, title = "" }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [sheet, setSheet] = useState(null);
  const [mode, setMode] = useState("best");
  const [nb, setNb] = useState(null);
  const [bk, setBk] = useState(null);

  useEffect(() => {
    setData(null);
    setErr(null);
    setSheet(null);
    poi(poiId).then(setData).catch((e) => setErr(e.message));
  }, [poiId]);

  if (err) return <ErrorBox message={err} />;
  if (!data) return <Loading label="Loading info…" />;

  const p = data.poi;
  const fact = data.facts?.[0]?.fact_text || p.description || "";

  async function openNearby() {
    setSheet("nearby");
    setNb(null);
    setMode("best");
    try {
      setNb(await nearby(poiId, "best"));
    } catch (e) {
      setNb({ error: e.message });
    }
  }
  async function openBook() {
    setSheet("book");
    setBk(null);
    try {
      setBk(await book(poiId));
    } catch (e) {
      setBk({ error: e.message });
    }
  }

  return (
    <Card>
      {title ? <Text style={s.h2}>{title}</Text> : null}
      <Text style={s.sub}>
        {p.poi_category} · {p.city_name}, {p.country_name}
      </Text>
      <Text style={s.desc}>{p.description}</Text>
      <View style={s.row}>
        <Text style={s.muted}>Entry</Text>
        <Text style={s.cost}>{p.entry_cost_display}</Text>
      </View>

      <View style={s.actions}>
        <Button label="Nearby" onPress={openNearby} />
        <Button label="Snap to Book" onPress={openBook} />
        <Button label="◉ AR View" variant="primary" onPress={() => onAR({ name: p.name, fact })} />
      </View>

      {data.facts?.length ? (
        <View style={s.block}>
          <Text style={s.kbTitle}>Grounded facts</Text>
          {data.facts.map((f, i) => (
            <View key={i} style={s.fact}>
              <Text style={s.factText}>{f.fact_text}</Text>
              <Chip text={f.confidence} tone={f.confidence === "high" ? "good" : "mid"} />
            </View>
          ))}
        </View>
      ) : null}
      {data.knowledge?.map((k, i) => (
        <View key={i} style={s.block}>
          <Text style={s.kbTitle}>{k.title}</Text>
          <Text style={s.kbBody}>{k.body}</Text>
        </View>
      ))}

      <Modal visible={sheet === "nearby"} animationType="slide" transparent onRequestClose={() => setSheet(null)}>
        <View style={s.sheetWrap}>
          <View style={s.sheet}>
            <View style={s.sheetHead}>
              <Text style={s.h2}>Nearby</Text>
              <TouchableOpacity onPress={() => setSheet(null)}>
                <Text style={{ color: C.accent, fontSize: 18, fontWeight: "800" }}>✕</Text>
              </TouchableOpacity>
            </View>
            <View style={s.tabs}>
              {["best", "walk", "cab"].map((m) => (
                <TouchableOpacity
                  key={m}
                  style={[s.tab, mode === m && s.tabActive]}
                  onPress={async () => {
                    setMode(m);
                    setNb(null);
                    try {
                      setNb(await nearby(poiId, m));
                    } catch (e) {
                      setNb({ error: e.message });
                    }
                  }}>
                  <Text style={[s.tabText, mode === m && s.tabTextActive]}>{m}</Text>
                </TouchableOpacity>
              ))}
            </View>
            <ScrollView style={{ maxHeight: 360 }}>
              {!nb ? (
                <Loading />
              ) : nb.error ? (
                <ErrorBox message={nb.error} />
              ) : (
                nb.nearby.map((r) => (
                  <View key={r.poi_id} style={s.nbItem}>
                    <View style={{ flex: 1 }}>
                      <Text style={s.nbName}>{r.name}</Text>
                      <Text style={s.muted}>
                        {r.minutes} min · {r.distance_km} km · {r.cost_display}
                      </Text>
                    </View>
                    <Text style={s.muted}>{Math.round(r.carbon_kg * 1000)}g CO₂</Text>
                  </View>
                ))
              )}
            </ScrollView>
          </View>
        </View>
      </Modal>

      <Modal visible={sheet === "book"} animationType="slide" transparent onRequestClose={() => setSheet(null)}>
        <View style={s.sheetWrap}>
          <View style={s.sheet}>
            <View style={s.sheetHead}>
              <Text style={s.h2}>Snap to Book</Text>
              <TouchableOpacity onPress={() => setSheet(null)}>
                <Text style={{ color: C.accent, fontSize: 18, fontWeight: "800" }}>✕</Text>
              </TouchableOpacity>
            </View>
            {bk ? (
              bk.error ? (
                <ErrorBox message={bk.error} />
              ) : (
                <View style={{ gap: 8 }}>
                  <Text style={s.h3}>{bk.name}</Text>
                  <Row k="Entry fee" v={bk.entry_cost_display} />
                  <Row k="Open hours" v={bk.opens_at ? `${bk.opens_at} – ${bk.closes_at || "late"}` : "variable"} />
                  {bk.closed_days ? <Row k="Closed" v={bk.closed_days} /> : null}
                  <Row k="Accessibility" v={bk.accessibility} />
                  <Row k="Best season" v={bk.best_season} />
                  <Row k="Typical visit" v={`${bk.typical_duration_minutes} min`} />
                  <Row k="CO₂ / visit" v={`${Math.round(bk.carbon_kg * 1000)}g`} />
                  <Row k="XR preview" v={bk.has_xr_scene ? "Available" : "Not available"} tone={bk.has_xr_scene ? C.good : C.muted} />
                  <Text style={[s.muted, { marginTop: 6 }]}>{bk.description}</Text>
                </View>
              )
            ) : (
              <Loading />
            )}
          </View>
        </View>
      </Modal>
    </Card>
  );
}

function Row({ k, v, tone }) {
  return (
    <View style={s.row}>
      <Text style={s.muted}>{k}</Text>
      <Text style={{ color: tone || C.text, fontWeight: "600" }}>{v}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  h2: { color: C.text, fontSize: 19, fontWeight: "800" },
  h3: { color: C.text, fontSize: 16, fontWeight: "700" },
  sub: { color: C.muted, fontSize: 13, marginTop: 2 },
  desc: { color: C.text, fontSize: 14, lineHeight: 20, marginVertical: 8 },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  muted: { color: C.muted, fontSize: 13 },
  cost: { color: C.accent, fontWeight: "800", fontSize: 15 },
  actions: { flexDirection: "row", gap: 8, marginVertical: 12 },
  block: { marginTop: 4 },
  kbTitle: { color: C.accent, fontWeight: "700", fontSize: 14, marginTop: 10, marginBottom: 4 },
  kbBody: { color: C.text, fontSize: 14, lineHeight: 20 },
  fact: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10, marginBottom: 8 },
  factText: { flex: 1, color: C.text, fontSize: 14, lineHeight: 19 },
  sheetWrap: { flex: 1, justifyContent: "flex-end", backgroundColor: "rgba(0,0,0,.55)" },
  sheet: {
    backgroundColor: C.panel,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 16,
    paddingBottom: 34,
    maxHeight: "75%",
  },
  sheetHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 10 },
  tabs: { flexDirection: "row", gap: 8, marginBottom: 10 },
  tab: { paddingHorizontal: 14, paddingVertical: 7, borderRadius: 999, backgroundColor: C.card, borderWidth: 1, borderColor: C.line },
  tabActive: { borderColor: C.accent },
  tabText: { color: C.muted, fontWeight: "700", textTransform: "capitalize" },
  tabTextActive: { color: C.accent },
  nbItem: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: C.line },
  nbName: { color: C.text, fontWeight: "600", fontSize: 14 },
});