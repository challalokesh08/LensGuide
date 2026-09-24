import React, { useEffect, useState } from "react";
import { FlatList, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { pois } from "./api";
import { C } from "./theme";
import { ErrorBox, Loading } from "./ui";
import POIView from "./POIView";

export default function ExploreScreen({ onAR }) {
  const [list, setList] = useState(null);
  const [err, setErr] = useState(null);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(null);

  useEffect(() => {
    pois().then(setList).catch((e) => setErr(e.message));
  }, []);

  if (err) return <ErrorBox message={err} />;
  if (!list) return <Loading label="Loading catalogue…" />;

  const filtered = q
    ? list.filter(
        (p) =>
          p.name.toLowerCase().includes(q.toLowerCase()) ||
          (p.city || "").toLowerCase().includes(q.toLowerCase())
      )
    : list;

  if (open) {
    return (
      <View style={{ flex: 1, padding: 14 }}>
        <TouchableOpacity onPress={() => setOpen(null)} style={{ marginBottom: 10 }}>
          <Text style={{ color: C.accent, fontSize: 15, fontWeight: "700" }}>← Back to list</Text>
        </TouchableOpacity>
        <POIView poiId={open.poi_id} onAR={onAR} title={open.name} />
      </View>
    );
  }

  return (
    <View style={{ flex: 1 }}>
      <TextInput
        value={q}
        onChangeText={setQ}
        placeholder="Search place or city…"
        placeholderTextColor={C.muted}
        style={s.search}
      />
      <FlatList
        data={filtered}
        keyExtractor={(i) => i.poi_id}
        contentContainerStyle={{ padding: 14, paddingBottom: 30 }}
        renderItem={({ item }) => (
          <TouchableOpacity style={s.item} onPress={() => setOpen(item)}>
            <View style={{ flex: 1 }}>
              <Text style={s.name}>{item.name}</Text>
              <Text style={s.sub}>
                {item.poi_category} · {item.city}
              </Text>
            </View>
            <Text style={{ color: C.accent, fontSize: 16 }}>›</Text>
          </TouchableOpacity>
        )}
      />
    </View>
  );
}

const s = StyleSheet.create({
  search: {
    backgroundColor: C.card,
    color: C.text,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: C.line,
    margin: 14,
    marginBottom: 0,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 15,
  },
  item: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: C.card,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: C.line,
    padding: 14,
    marginBottom: 8,
  },
  name: { color: C.text, fontSize: 15, fontWeight: "700" },
  sub: { color: C.muted, fontSize: 12, marginTop: 2 },
});