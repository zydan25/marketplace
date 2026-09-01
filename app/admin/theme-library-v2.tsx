import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { router } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, RefreshControl, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { AdminLayout, Colors, Font, Shadow, Spacing } from "@/components/admin";
import { djangoApi } from "@/lib/django-api";

type Config = Record<string, any>;
type Theme = { id: number; name: string; is_global: boolean; is_active: boolean; tokens: Config; layout: Config; sections: Config[] };
type Preset = { name: string; description?: string; tokens: Config; layout: Config; sections: Config[] };

function presetColor(preset: Preset | undefined, key: string) {
  return String(preset?.tokens?.primary ?? (key === "electronics" ? "#0D47A1" : "#E60023"));
}

export default function ThemeLibraryV2() {
  const [themes, setThemes] = useState<Theme[]>([]);
  const [presets, setPresets] = useState<Record<string, Preset>>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [themeResponse, presetResponse] = await Promise.all([
        djangoApi<{ results?: Theme[] }>("/api/themes/"),
        djangoApi<Record<string, Preset>>("/api/themes/presets/"),
      ]);
      setThemes(themeResponse.results ?? []);
      setPresets(presetResponse ?? {});
    } catch {
      setThemes([]);
      setPresets({});
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function install(key: string) {
    setBusy(key);
    try {
      const created = await djangoApi<Theme>("/api/themes/install_preset/", { method: "POST", body: JSON.stringify({ preset: key, name: presets[key]?.name }) });
      await djangoApi(`/api/themes/${created.id}/activate/`, { method: "POST" });
      await load();
      router.push(`/admin/theme-builder?theme=${created.id}` as never);
    } finally {
      setBusy(null);
    }
  }

  async function activate(theme: Theme) {
    setBusy(`activate:${theme.id}`);
    try {
      await djangoApi(`/api/themes/${theme.id}/activate/`, { method: "POST" });
      await load();
    } finally {
      setBusy(null);
    }
  }

  async function duplicate(theme: Theme) {
    setBusy(`duplicate:${theme.id}`);
    try {
      const copy = await djangoApi<Theme>(`/api/themes/${theme.id}/duplicate/`, { method: "POST", body: JSON.stringify({ name: `نسخة — ${theme.name}` }) });
      router.push(`/admin/theme-builder?theme=${copy.id}` as never);
    } finally {
      setBusy(null);
    }
  }

  const presetKeys = Object.keys(presets);

  return <AdminLayout title="مكتبة تصاميم المتجر">
    <ScrollView style={{ flex: 1 }} contentContainerStyle={styles.page} refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor={Colors.primary} />}>
      <View style={styles.hero}>
        <View style={styles.heroIcon}><MaterialIcons name="style" size={25} color="#FFF" /></View>
        <View style={styles.heroCopy}><Text style={styles.heroTitle}>مكتبة التصاميم</Text><Text style={styles.heroText}>قوالب جاهزة قابلة للاستخدام والنسخ والتخصيص. أي قالب جديد يضيفه الخادم يظهر هنا تلقائيًا.</Text></View>
        <TouchableOpacity style={styles.heroButton} onPress={() => router.push("/admin/theme-builder" as never)}><MaterialIcons name="dashboard-customize" size={16} color="#FFF" /><Text style={styles.heroButtonText}>فتح المصمم</Text></TouchableOpacity>
      </View>

      <View style={styles.sectionHead}><View><Text style={styles.title}>القوالب الجاهزة</Text><Text style={styles.sub}>يمكن إضافة قوالب جديدة لاحقًا من طبقة الـpresets دون إعادة بناء واجهة المكتبة.</Text></View></View>
      {loading && presetKeys.length === 0 ? <ActivityIndicator color={Colors.primary} style={{ margin: 30 }} /> : <View style={styles.grid}>
        {presetKeys.map((key) => {
          const preset = presets[key];
          const color = presetColor(preset, key);
          const active = themes.some((theme) => theme.is_global && theme.is_active && theme.layout?.family === preset?.layout?.family);
          return <View key={key} style={[styles.preset, { borderColor: `${color}35`, backgroundColor: String(preset?.tokens?.background ?? "#FFF") }]}>
            <PreviewMini family={String(preset?.layout?.family ?? key)} color={color} />
            <Text style={styles.presetTitle}>{preset?.name ?? key}</Text>
            <Text style={styles.presetSub}>{preset?.description ?? ""}</Text>
            <View style={styles.actionsRow}>
              <TouchableOpacity disabled={!!busy} style={[styles.primaryAction, { backgroundColor: color }]} onPress={() => void install(key)}>{busy === key ? <ActivityIndicator color="#FFF" /> : <><MaterialIcons name="add-circle" size={16} color="#FFF" /><Text style={styles.primaryText}>{active ? "إنشاء نسخة" : "استخدام القالب"}</Text></>}</TouchableOpacity>
              {active ? <View style={styles.activeBadge}><MaterialIcons name="check-circle" size={15} color={Colors.success} /><Text style={styles.activeText}>نشط</Text></View> : null}
            </View>
          </View>;
        })}
      </View>}

      <View style={styles.card}><View style={styles.sectionHead}><View><Text style={styles.title}>التصاميم المحفوظة</Text><Text style={styles.sub}>كل نسخة مستقلة ويمكن فتحها في المصمم وتفعيلها.</Text></View></View>
        {themes.length === 0 && !loading ? <Text style={styles.empty}>لا توجد تصاميم محفوظة.</Text> : themes.map((theme) => <View key={theme.id} style={styles.themeRow}><View style={[styles.swatch, { backgroundColor: String(theme.tokens?.primary ?? Colors.primary) }]}><MaterialIcons name="palette" size={16} color="#FFF" /></View><View style={styles.themeCopy}><Text style={styles.themeName}>{theme.name}</Text><Text style={styles.themeMeta}>{theme.layout?.family ?? "custom"} · {theme.is_active ? "نشط" : "غير نشط"}</Text></View><TouchableOpacity disabled={!!busy || theme.is_active} style={styles.secondaryButton} onPress={() => void activate(theme)}><Text style={styles.secondaryText}>{theme.is_active ? "نشط" : "تفعيل"}</Text></TouchableOpacity><TouchableOpacity disabled={!!busy} style={styles.secondaryButton} onPress={() => void duplicate(theme)}><Text style={styles.secondaryText}>نسخ وتعديل</Text></TouchableOpacity><TouchableOpacity disabled={!!busy} style={styles.secondaryButton} onPress={() => router.push(`/admin/theme-builder?theme=${theme.id}` as never)}><Text style={styles.secondaryText}>فتح المصمم</Text></TouchableOpacity></View>)}
      </View>
    </ScrollView>
  </AdminLayout>;
}

function PreviewMini({ family, color }: { family: string; color: string }) {
  return <View style={[styles.preview, { backgroundColor: family === "electronics" ? "#F3F8FF" : "#FFF7F8" }]}><View style={styles.previewHeader}><View style={[styles.previewLogo, { backgroundColor: color }]} /><View style={styles.previewSearch} /><View style={styles.previewDot} /><View style={styles.previewDot} /></View><View style={[styles.previewHero, { backgroundColor: color }]}><View style={styles.previewLineLong} /><View style={styles.previewLineShort} /><View style={styles.previewImage} /></View><View style={styles.previewCircles}>{[1,2,3,4,5].map((item) => <View key={item} style={[styles.previewCircle, { borderColor: `${color}40` }]} />)}</View><View style={styles.previewProducts}>{[1,2,3,4].map((item) => <View key={item} style={styles.previewProduct} />)}</View></View>;
}

const styles = StyleSheet.create({
  page: { padding: Spacing.md, paddingBottom: 110 },
  hero: { backgroundColor: "#101828", borderRadius: 22, padding: 18, flexDirection: "row-reverse", alignItems: "center", gap: 12, marginBottom: 16, ...Shadow.md },
  heroIcon: { width: 48, height: 48, borderRadius: 15, backgroundColor: Colors.primary, alignItems: "center", justifyContent: "center" },
  heroCopy: { flex: 1, alignItems: "flex-end" }, heroTitle: { color: "#FFF", fontSize: 20, fontWeight: "900", textAlign: "right" }, heroText: { color: "#C9D1DB", fontSize: 10, lineHeight: 18, textAlign: "right", marginTop: 4 }, heroButton: { height: 38, paddingHorizontal: 11, borderRadius: 10, backgroundColor: Colors.primary, flexDirection: "row-reverse", alignItems: "center", gap: 5 }, heroButtonText: { color: "#FFF", fontSize: 9, fontWeight: "900" },
  sectionHead: { flexDirection: "row-reverse", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }, title: { color: Colors.text, ...Font.sectionTitle, textAlign: "right" }, sub: { color: Colors.textSecondary, ...Font.small, textAlign: "right", marginTop: 2 },
  grid: { flexDirection: "row-reverse", flexWrap: "wrap", gap: 12 }, preset: { flexGrow: 1, flexBasis: 330, minWidth: 290, borderWidth: 1, borderRadius: 18, padding: 11 }, preview: { minHeight: 180, borderRadius: 12, padding: 8 }, previewHeader: { height: 22, borderRadius: 8, backgroundColor: "#FFF", flexDirection: "row-reverse", alignItems: "center", gap: 4, paddingHorizontal: 6 }, previewLogo: { width: 16, height: 16, borderRadius: 5 }, previewSearch: { flex: 1, height: 14, borderWidth: 1, borderColor: "#E5E7EB", borderRadius: 8 }, previewDot: { width: 13, height: 13, borderRadius: 7, backgroundColor: "#E5E7EB" }, previewHero: { height: 72, borderRadius: 8, marginTop: 6, padding: 6, flexDirection: "row-reverse", alignItems: "center", justifyContent: "space-between" }, previewLineLong: { width: "43%", height: 8, borderRadius: 5, backgroundColor: "#FFF" }, previewLineShort: { width: "26%", height: 5, borderRadius: 5, backgroundColor: "#FFFFFF80", position: "absolute", right: 8, bottom: 9 }, previewImage: { width: "47%", height: "86%", borderRadius: 7, backgroundColor: "#FFFFFF35" }, previewCircles: { flexDirection: "row-reverse", gap: 5, marginTop: 7 }, previewCircle: { width: 32, height: 32, borderRadius: 16, backgroundColor: "#FFF", borderWidth: 1 }, previewProducts: { flexDirection: "row-reverse", gap: 5, marginTop: 7 }, previewProduct: { flex: 1, height: 37, borderRadius: 7, backgroundColor: "#FFF", borderWidth: 1, borderColor: "#E5E7EB" }, presetTitle: { fontSize: 13, fontWeight: "900", color: Colors.text, textAlign: "right", marginTop: 9 }, presetSub: { fontSize: 9, color: Colors.textSecondary, lineHeight: 16, textAlign: "right", marginTop: 3, minHeight: 30 }, actionsRow: { marginTop: 9, gap: 7 }, primaryAction: { height: 40, borderRadius: 10, flexDirection: "row-reverse", alignItems: "center", justifyContent: "center", gap: 5 }, primaryText: { color: "#FFF", fontSize: 10, fontWeight: "900" }, activeBadge: { height: 34, borderRadius: 10, backgroundColor: Colors.successLight, flexDirection: "row-reverse", alignItems: "center", justifyContent: "center", gap: 5 }, activeText: { color: Colors.success, fontSize: 9, fontWeight: "900" },
  card: { backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.divider, borderRadius: 18, padding: 13, marginTop: 14, ...Shadow.sm }, themeRow: { minHeight: 56, flexDirection: "row-reverse", alignItems: "center", gap: 7, borderTopWidth: 1, borderTopColor: Colors.divider }, swatch: { width: 35, height: 35, borderRadius: 11, alignItems: "center", justifyContent: "center" }, themeCopy: { flex: 1, alignItems: "flex-end" }, themeName: { fontSize: 11, fontWeight: "900", color: Colors.text }, themeMeta: { fontSize: 8, color: Colors.textSecondary, marginTop: 2 }, secondaryButton: { height: 33, paddingHorizontal: 9, borderRadius: 9, backgroundColor: Colors.surfaceAlt, alignItems: "center", justifyContent: "center" }, secondaryText: { fontSize: 8, color: Colors.text, fontWeight: "900" }, empty: { paddingVertical: 22, color: Colors.textSecondary, textAlign: "right", fontSize: 10 },
});
