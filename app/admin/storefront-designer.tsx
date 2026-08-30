import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Alert, RefreshControl, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";

import { AdminLayout, Colors, Font, Radius, Shadow, Spacing } from "@/components/admin";
import { useAuth } from "@/hooks/use-auth";
import { djangoApi } from "@/lib/django-api";

const PRESET_META = [
  {
    key: "fashion",
    title: "التصميم العام 1 — Fashion",
    subtitle: "النسخة البيضاء ذات الصور الكبيرة والفئات الدائرية والتبويبات.",
    accent: "#E60023",
    bg: "#FFFFFF",
    chips: ["Hero كبير", "فئات دائرية", "تبويبات", "تخفيضات"],
  },
  {
    key: "electronics",
    title: "التصميم العام 2 — Electronics",
    subtitle: "النسخة الزرقاء ذات شريط الأقسام والبنر العريض وشبكة المنتجات.",
    accent: "#0D47A1",
    bg: "#F4F8FF",
    chips: ["شريط أقسام", "بنر عريض", "شبكة فئات", "أجهزة"],
  },
] as const;

type Theme = {
  id: number;
  name: string;
  is_global: boolean;
  is_active: boolean;
  tokens: Record<string, any>;
  layout: Record<string, any>;
  sections: Record<string, any>[];
};

type Preset = {
  name: string;
  tokens: Record<string, any>;
  layout: Record<string, any>;
  sections: Record<string, any>[];
};

export default function StorefrontDesignerScreen() {
  useAuth();
  const [themes, setThemes] = useState<Theme[]>([]);
  const [presets, setPresets] = useState<Record<string, Preset>>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [newThemeName, setNewThemeName] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [themeResponse, presetResponse] = await Promise.all([
        djangoApi<{ results?: Theme[] }>("/api/themes/"),
        djangoApi<Record<string, Preset>>("/api/themes/presets/"),
      ]);
      const next = themeResponse.results ?? [];
      setThemes(next);
      setPresets(presetResponse ?? {});
      setSelectedId(current => current && next.some(x => x.id === current) ? current : next.find(x => x.is_global && x.is_active)?.id ?? next[0]?.id ?? null);
    } catch (error) {
      Alert.alert("تعذر تحميل المصمم", error instanceof Error ? error.message : "حاول مرة أخرى.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const activeGlobal = useMemo(() => themes.find(t => t.is_global && t.is_active) ?? null, [themes]);
  const selected = useMemo(() => themes.find(t => t.id === selectedId) ?? null, [selectedId, themes]);

  async function install(key: string) {
    setBusy(`install:${key}`);
    try {
      const name = newThemeName.trim() || presets[key]?.name || key;
      const theme = await djangoApi<Theme>("/api/themes/install_preset/", { method: "POST", body: JSON.stringify({ preset: key, name }) });
      setNewThemeName("");
      setThemes(items => [theme, ...items]);
      setSelectedId(theme.id);
      Alert.alert("تم إنشاء التصميم", "أصبح التصميم نسخة مستقلة ويمكن تعديلها دون تغيير القالب العام الأصلي.");
    } catch (error) {
      Alert.alert("تعذر إنشاء التصميم", error instanceof Error ? error.message : "حاول مرة أخرى.");
    } finally { setBusy(null); }
  }

  async function activate(theme: Theme) {
    setBusy(`activate:${theme.id}`);
    try {
      const updated = await djangoApi<Theme>(`/api/themes/${theme.id}/activate/`, { method: "POST" });
      setThemes(items => items.map(item => item.id === updated.id ? updated : { ...item, is_active: item.is_global ? false : item.is_active }));
      Alert.alert("تم التفعيل", `التصميم النشط الآن: ${updated.name}`);
    } catch (error) {
      Alert.alert("تعذر التفعيل", error instanceof Error ? error.message : "حاول مرة أخرى.");
    } finally { setBusy(null); }
  }

  async function duplicate(theme: Theme) {
    setBusy(`duplicate:${theme.id}`);
    try {
      const updated = await djangoApi<Theme>(`/api/themes/${theme.id}/duplicate/`, { method: "POST", body: JSON.stringify({ name: newThemeName.trim() || `نسخة — ${theme.name}` }) });
      setNewThemeName("");
      setThemes(items => [updated, ...items]);
      setSelectedId(updated.id);
    } catch (error) {
      Alert.alert("تعذر نسخ التصميم", error instanceof Error ? error.message : "حاول مرة أخرى.");
    } finally { setBusy(null); }
  }

  async function saveSelected(patch: Partial<Theme>) {
    if (!selected) return;
    setBusy(`save:${selected.id}`);
    try {
      const updated = await djangoApi<Theme>(`/api/themes/${selected.id}/`, { method: "PATCH", body: JSON.stringify(patch) });
      setThemes(items => items.map(item => item.id === updated.id ? updated : item));
    } catch (error) {
      Alert.alert("تعذر حفظ التصميم", error instanceof Error ? error.message : "حاول مرة أخرى.");
    } finally { setBusy(null); }
  }

  return (
    <AdminLayout title="مصمم واجهة المتجر">
      <ScrollView style={{ flex: 1 }} contentContainerStyle={styles.page} showsVerticalScrollIndicator={false} refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor={Colors.primary} />}>
        <View style={styles.hero}>
          <View style={styles.heroIcon}><MaterialIcons name="dashboard-customize" size={27} color="#FFF" /></View>
          <View style={styles.heroCopy}>
            <Text style={styles.heroTitle}>المصمم الرئيسي للواجهة</Text>
            <Text style={styles.heroText}>هنا تختار الشكل العام للمنصة وتدير نسخ التصميم. المحتوى نفسه يبقى قابلًا للتعديل من محرر الأقسام.</Text>
          </View>
          <TouchableOpacity style={styles.darkButton} onPress={() => router.push("/admin/storefront" as never)}><MaterialIcons name="view-quilt" size={18} color="#FFF" /><Text style={styles.darkButtonText}>فتح محرر الأقسام</Text></TouchableOpacity>
        </View>

        <View style={styles.sectionHead}><Text style={styles.sectionTitle}>التصميمان العامان الجاهزان</Text><Text style={styles.sectionHint}>لا يتم تعديل النسخة الأصلية عند التثبيت</Text></View>
        <View style={styles.presetRow}>
          {PRESET_META.map(preset => {
            const p = presets[preset.key];
            return (
              <View key={preset.key} style={[styles.presetCard, { backgroundColor: preset.bg }]}>
                <View style={styles.mockHeader}>
                  <View style={styles.mockLogo} />
                  <View style={[styles.mockSearch, { borderColor: `${preset.accent}30` }]} />
                  <View style={styles.mockIcon} /><View style={styles.mockIcon} />
                </View>
                <View style={[styles.mockHero, { backgroundColor: preset.accent }]}>
                  <View style={styles.mockHeroText}><View style={styles.mockLineLg}/><View style={styles.mockLineSm}/></View>
                  <View style={styles.mockImage}/>
                </View>
                <View style={styles.mockChips}>{preset.chips.map((chip,index)=><View key={chip} style={[styles.mockChip,{backgroundColor:index===0?preset.accent:"#FFF",borderColor:`${preset.accent}35`}]}><Text style={[styles.mockChipText,{color:index===0?"#FFF":preset.accent}]}>{chip}</Text></View>)}</View>
                <Text style={styles.presetTitle}>{preset.title}</Text>
                <Text style={styles.presetSubtitle}>{preset.subtitle}</Text>
                <TouchableOpacity disabled={!!busy || !p} onPress={() => install(preset.key)} style={[styles.primaryButton,{backgroundColor:preset.accent}]}>
                  {busy === `install:${preset.key}` ? <ActivityIndicator color="#FFF"/> : <><MaterialIcons name="add-circle-outline" size={18} color="#FFF"/><Text style={styles.primaryButtonText}>استخدام هذا التصميم</Text></>}
                </TouchableOpacity>
              </View>
            );
          })}
        </View>

        <View style={styles.sectionHead}><Text style={styles.sectionTitle}>تصميماتي</Text><Text style={styles.sectionHint}>{themes.length} تصميم</Text></View>
        <View style={styles.card}>
          {loading ? <ActivityIndicator color={Colors.primary} style={{ marginVertical: 30 }} /> : themes.length === 0 ? <Text style={styles.empty}>ثبّت أحد التصميمين من الأعلى للبدء.</Text> : themes.map(theme => (
            <TouchableOpacity key={theme.id} onPress={() => setSelectedId(theme.id)} style={[styles.themeRow, selected?.id === theme.id && styles.themeRowActive]}>
              <View style={[styles.themeSwatch,{backgroundColor:String(theme.tokens?.primary??Colors.primary)}]}><MaterialIcons name="palette" size={18} color="#FFF"/></View>
              <View style={styles.themeCopy}><Text style={styles.themeName}>{theme.name}</Text><Text style={styles.themeMeta}>{theme.is_global ? "عام" : "خاص"} · {theme.layout?.family || "custom"}</Text></View>
              {theme.is_active ? <View style={styles.activePill}><Text style={styles.activeText}>مفعل</Text></View> : <Text style={styles.inactiveText}>غير مفعل</Text>}
            </TouchableOpacity>
          ))}
        </View>

        {selected ? <View style={styles.card}>
          <View style={styles.detailHead}><View><Text style={styles.sectionTitle}>تخصيص: {selected.name}</Text><Text style={styles.sectionHint}>التعديل هنا يخص النسخة المحددة فقط.</Text></View><View style={styles.actions}>
            {!selected.is_active && <TouchableOpacity disabled={!!busy} style={styles.smallPrimary} onPress={() => activate(selected)}>{busy === `activate:${selected.id}` ? <ActivityIndicator color="#FFF"/> : <Text style={styles.smallPrimaryText}>تفعيل</Text>}</TouchableOpacity>}
            <TouchableOpacity disabled={!!busy} style={styles.smallButton} onPress={() => duplicate(selected)}>{busy === `duplicate:${selected.id}` ? <ActivityIndicator color="#111"/> : <><MaterialIcons name="content-copy" size={16} color="#111"/><Text style={styles.smallButtonText}>نسخ</Text></>}</TouchableOpacity>
          </View></View>
          <View style={styles.formGrid}>
            <View style={styles.field}><Text style={styles.label}>اسم التصميم</Text><TextInput defaultValue={selected.name} onEndEditing={e => saveSelected({ name: e.nativeEvent.text })} style={styles.input} textAlign="right" /></View>
            <View style={styles.field}><Text style={styles.label}>اللون الرئيسي</Text><TextInput defaultValue={String(selected.tokens?.primary ?? "")} onEndEditing={e => saveSelected({ tokens: { ...selected.tokens, primary: e.nativeEvent.text } })} style={styles.input} textAlign="right" /></View>
            <View style={styles.field}><Text style={styles.label}>الخلفية</Text><TextInput defaultValue={String(selected.tokens?.background ?? "#FFFFFF")} onEndEditing={e => saveSelected({ tokens: { ...selected.tokens, background: e.nativeEvent.text } })} style={styles.input} textAlign="right" /></View>
            <View style={styles.field}><Text style={styles.label}>شكل البطاقات</Text><TextInput defaultValue={String(selected.layout?.product_card ?? "rounded")} onEndEditing={e => saveSelected({ layout: { ...selected.layout, product_card: e.nativeEvent.text } })} style={styles.input} textAlign="right" /></View>
          </View>
          <View style={styles.info}><MaterialIcons name="info-outline" size={18} color={Colors.info}/><Text style={styles.infoText}>المحتوى، البنرات، الفئات، الصفوف والأعمدة وإعدادات الأقسام تُدار من محرر الواجهة، ولا تتغير عند اختيار تصميم آخر إلا في خصائص الشكل.</Text></View>
        </View> : null}
      </ScrollView>
    </AdminLayout>
  );
}

const styles = StyleSheet.create({
  page:{padding:Spacing.md,paddingBottom:100},hero:{backgroundColor:"#111827",borderRadius:22,padding:18,flexDirection:"row-reverse",alignItems:"center",gap:12,marginBottom:18,...Shadow.md},heroIcon:{width:48,height:48,borderRadius:15,backgroundColor:"#E60023",alignItems:"center",justifyContent:"center"},heroCopy:{flex:1,alignItems:"flex-end"},heroTitle:{color:"#FFF",fontSize:19,fontWeight:"900",textAlign:"right"},heroText:{color:"#C7CEDB",fontSize:10,lineHeight:17,textAlign:"right",marginTop:4},darkButton:{height:40,borderRadius:12,backgroundColor:"#1F2937",borderWidth:1,borderColor:"#374151",paddingHorizontal:12,flexDirection:"row-reverse",alignItems:"center",gap:6},darkButtonText:{color:"#FFF",fontSize:10,fontWeight:"900"},sectionHead:{flexDirection:"row-reverse",justifyContent:"space-between",alignItems:"baseline",marginBottom:9,marginTop:3},sectionTitle:{color:Colors.text,...Font.sectionTitle,textAlign:"right"},sectionHint:{color:Colors.textSecondary,...Font.small,textAlign:"right"},presetRow:{flexDirection:"row-reverse",gap:10,flexWrap:"wrap",marginBottom:16},presetCard:{flexGrow:1,flexBasis:320,minWidth:280,borderRadius:18,borderWidth:1,borderColor:"#E6E8EC",padding:12,...Shadow.sm},mockHeader:{height:36,backgroundColor:"#FFF",borderRadius:10,flexDirection:"row-reverse",alignItems:"center",paddingHorizontal:8,gap:5},mockLogo:{width:22,height:22,borderRadius:7,backgroundColor:"#111"},mockSearch:{flex:1,height:22,borderRadius:12,borderWidth:1},mockIcon:{width:18,height:18,borderRadius:9,backgroundColor:"#E7E7E7"},mockHero:{height:122,borderRadius:12,marginTop:8,overflow:"hidden",flexDirection:"row-reverse",alignItems:"center",justifyContent:"space-between",padding:10},mockHeroText:{width:"40%",gap:8,alignItems:"flex-end"},mockLineLg:{height:10,width:"85%",borderRadius:5,backgroundColor:"#FFF"},mockLineSm:{height:6,width:"60%",borderRadius:4,backgroundColor:"#FFFFFF99"},mockImage:{width:"47%",height:"90%",borderRadius:10,backgroundColor:"#FFFFFF33"},mockChips:{flexDirection:"row-reverse",flexWrap:"wrap",gap:5,marginTop:8},mockChip:{paddingHorizontal:7,paddingVertical:4,borderRadius:11,borderWidth:1},mockChipText:{fontSize:7,fontWeight:"800"},presetTitle:{fontSize:14,fontWeight:"900",color:Colors.text,textAlign:"right",marginTop:11},presetSubtitle:{fontSize:9,color:Colors.textSecondary,textAlign:"right',marginTop:4,lineHeight:16},primaryButton:{height:42,borderRadius:12,marginTop:11,flexDirection:"row-reverse",alignItems:"center",justifyContent:"center",gap:6},primaryButtonText:{color:"#FFF",fontSize:11,fontWeight:"900"},card:{backgroundColor:Colors.surface,borderRadius:18,borderWidth:1,borderColor:Colors.divider,padding:14,marginBottom:14,...Shadow.sm},themeRow:{flexDirection:"row-reverse",alignItems:"center",gap:9,paddingVertical:10,borderBottomWidth:1,borderBottomColor:Colors.divider},themeRowActive:{backgroundColor:Colors.surfaceAlt,borderRadius:12,paddingHorizontal:9},themeSwatch:{width:36,height:36,borderRadius:11,alignItems:"center",justifyContent:"center"},themeCopy:{flex:1,alignItems:"flex-end"},themeName:{fontSize:12,fontWeight:"900",color:Colors.text},themeMeta:{fontSize:9,color:Colors.textSecondary,marginTop:2},activePill:{backgroundColor:Colors.successLight,paddingHorizontal:8,paddingVertical:5,borderRadius:999},activeText:{fontSize:9,fontWeight:"900",color:Colors.success},inactiveText:{fontSize:9,color:Colors.textSecondary},detailHead:{flexDirection:"row-reverse",justifyContent:"space-between",gap:10,alignItems:"center",marginBottom:12},actions:{flexDirection:"row-reverse",gap:7},smallPrimary:{minWidth:72,height:38,borderRadius:10,backgroundColor:Colors.primary,alignItems:"center",justifyContent:"center",paddingHorizontal:10},smallPrimaryText:{color:"#FFF",fontSize:10,fontWeight:"900"},smallButton:{height:38,borderRadius:10,borderWidth:1,borderColor:Colors.divider,paddingHorizontal:10,flexDirection:"row-reverse",alignItems:"center",gap:5},smallButtonText:{fontSize:10,fontWeight:"900",color:Colors.text},formGrid:{flexDirection:"row-reverse",flexWrap:"wrap",gap:8},field:{flexGrow:1,minWidth:160,gap:5},label:{fontSize:9,fontWeight:"900",color:Colors.text,textAlign:"right"},input:{height:44,borderWidth:1,borderColor:Colors.divider,borderRadius:10,paddingHorizontal:11,color:Colors.text,backgroundColor:Colors.surfaceAlt},info:{marginTop:12,backgroundColor:Colors.infoLight,borderRadius:12,padding:10,flexDirection:"row-reverse",gap:7,alignItems:"flex-start"},infoText:{flex:1,fontSize:9,color:Colors.info,textAlign:"right",lineHeight:16},empty:{textAlign:"center",color:Colors.textSecondary,padding:25,fontSize:11}
});
