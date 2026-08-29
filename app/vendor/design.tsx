import { useEffect, useMemo, useState } from "react";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { router } from "expo-router";
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { ScreenContainer } from "@/components/screen-container";
import { djangoApi } from "@/lib/django-api";

type Theme = {
  id: number;
  name: string;
  vendor?: number | null;
  is_global?: boolean;
  tokens: Record<string, string>;
  layout: Record<string, unknown>;
  sections?: unknown;
  is_active: boolean;
};

type Palette = {
  id: string;
  name: string;
  primary: string;
  background: string;
};

const PALETTES: Palette[] = [
  { id: "shopik-red", name: "شُبيك", primary: "#E60023", background: "#F6F7F9" },
  { id: "ocean", name: "محيط", primary: "#1769E0", background: "#F3F7FC" },
  { id: "emerald", name: "زمرد", primary: "#168451", background: "#F1F7F3" },
  { id: "violet", name: "بنفسجي", primary: "#7652E8", background: "#F7F5FC" },
  { id: "sand", name: "رملي", primary: "#B5651D", background: "#FBF6EF" },
];

const DEFAULT_PALETTE = PALETTES[0];

function validHex(value: string) {
  return /^#[0-9a-fA-F]{6}$/.test(value.trim());
}

function safeHex(value: unknown, fallback: string) {
  return typeof value === "string" && validHex(value) ? value.toUpperCase() : fallback;
}

export default function VendorDesignScreen() {
  const [theme, setTheme] = useState<Theme | null>(null);
  const [name, setName] = useState("هوية متجري");
  const [primary, setPrimary] = useState(DEFAULT_PALETTE.primary);
  const [background, setBackground] = useState(DEFAULT_PALETTE.background);
  const [showHero, setShowHero] = useState(true);
  const [showCategories, setShowCategories] = useState(true);
  const [showFlashSale, setShowFlashSale] = useState(true);
  const [showProducts, setShowProducts] = useState(true);
  const [radius, setRadius] = useState("16");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let mounted = true;
    djangoApi<{ results?: Theme[] }>("/api/themes/")
      .then((data) => {
        if (!mounted) return;
        const own = (data.results ?? []).find((item) => item.is_global === false || Boolean(item.vendor));
        if (!own) return;
        setTheme(own);
        setName(own.name || "هوية متجري");
        setPrimary(safeHex(own.tokens?.primary, DEFAULT_PALETTE.primary));
        setBackground(safeHex(own.tokens?.background, DEFAULT_PALETTE.background));
        setShowHero(own.layout?.showHero !== false);
        setShowCategories(own.layout?.showCategories !== false);
        setShowFlashSale(own.layout?.showFlashSale !== false);
        setShowProducts(own.layout?.showProducts !== false);
        const storedRadius = Number(own.layout?.radius ?? 16);
        setRadius(String(Number.isFinite(storedRadius) ? Math.min(28, Math.max(8, storedRadius)) : 16));
      })
      .catch(() => undefined)
      .finally(() => mounted && setLoading(false));
    return () => {
      mounted = false;
    };
  }, []);

  const selectedPalette = useMemo(() => {
    return PALETTES.find((palette) => palette.primary === primary && palette.background === background)?.id ?? "custom";
  }, [background, primary]);

  const radiusValue = useMemo(() => {
    const parsed = Number(radius);
    return Number.isFinite(parsed) ? Math.min(28, Math.max(8, parsed)) : 16;
  }, [radius]);

  function applyPalette(palette: Palette) {
    setPrimary(palette.primary);
    setBackground(palette.background);
  }

  async function save() {
    if (!validHex(primary) || !validHex(background)) {
      Alert.alert("لون غير صالح", "استخدم رمز اللون بالشكل #RRGGBB.");
      return;
    }
    setSaving(true);
    try {
      const payload = {
        name: name.trim() || "هوية متجري",
        is_active: true,
        tokens: { primary: primary.trim().toUpperCase(), background: background.trim().toUpperCase(), surface: "#FFFFFF", owner: "vendor" },
        layout: { showHero, showCategories, showFlashSale, showProducts, productGrid: 2, radius: radiusValue, direction: "rtl" },
        sections: [
          ...(showHero ? ["hero"] : []),
          ...(showCategories ? ["categories"] : []),
          ...(showFlashSale ? ["flash_sale"] : []),
          ...(showProducts ? ["products"] : []),
        ],
      };
      const result = theme
        ? await djangoApi<Theme>(`/api/themes/${theme.id}/`, { method: "PATCH", body: JSON.stringify(payload) })
        : await djangoApi<Theme>("/api/themes/", { method: "POST", body: JSON.stringify(payload) });
      setTheme(result);
      Alert.alert("تم الحفظ", "تم نشر هوية المتجر الجديدة.");
    } catch (error) {
      Alert.alert("تعذر الحفظ", error instanceof Error ? error.message : "حدث خطأ أثناء حفظ التصميم.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <ScreenContainer>
        <View style={styles.center}>
          <ActivityIndicator color="#E60023" />
          <Text style={styles.loadingText}>جارٍ تحميل مصمم المتجر...</Text>
        </View>
      </ScreenContainer>
    );
  }

  return (
    <ScreenContainer edges={["top", "bottom", "left", "right"]} style={styles.page}>
      <View style={styles.header}>
        <TouchableOpacity style={styles.headerIcon} onPress={() => router.back()}>
          <MaterialIcons name="arrow-forward" size={23} color="#15171C" />
        </TouchableOpacity>
        <View style={styles.headerCenter}>
          <Text style={styles.headerTitle}>مصمم واجهة المتجر</Text>
          <Text style={styles.headerSub}>الهوية والألوان والتحكم السريع في عرض المتجر</Text>
        </View>
        <TouchableOpacity style={styles.headerPreview} onPress={() => router.push("/vendor/storefront" as never)}>
          <MaterialIcons name="visibility" size={18} color={primary} />
          <Text style={[styles.headerPreviewText, { color: primary }]}>معاينة</Text>
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.heroBanner}>
          <View style={[styles.heroOrb, { backgroundColor: primary }]} />
          <View style={styles.heroCopy}>
            <View style={styles.eyebrow}>
              <MaterialIcons name="auto-awesome" size={14} color={primary} />
              <Text style={[styles.eyebrowText, { color: primary }]}>هوية جاهزة للنشر</Text>
            </View>
            <Text style={styles.heroTitle}>اجعل متجرك يبدو مثل علامتك التجارية</Text>
            <Text style={styles.heroDescription}>اختر هوية متناسقة، عدّل الألوان، وحدد ما يظهر في واجهة العملاء. التصميم هنا مرتبط مباشرة بعقد Django الحالي.</Text>
            <View style={styles.heroActions}>
              <TouchableOpacity style={[styles.primaryAction, { backgroundColor: primary }]} onPress={save} disabled={saving}>
                {saving ? <ActivityIndicator color="#FFF" /> : <><MaterialIcons name="publish" size={18} color="#FFF" /><Text style={styles.primaryActionText}>حفظ ونشر</Text></>}
              </TouchableOpacity>
              <TouchableOpacity style={styles.secondaryAction} onPress={() => router.push("/vendor/storefront" as never)}>
                <MaterialIcons name="dashboard-customize" size={18} color="#15171C" />
                <Text style={styles.secondaryActionText}>محرر الأقسام</Text>
              </TouchableOpacity>
            </View>
          </View>
          <View style={styles.previewWrap}>
            <View style={[styles.phone, { borderRadius: radiusValue + 8 }]}>
              <View style={[styles.phoneTop, { backgroundColor: primary }]}>
                <View style={styles.phoneLogo}><MaterialIcons name="storefront" size={17} color={primary} /></View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.phoneName} numberOfLines={1}>{name || "متجري"}</Text>
                  <Text style={styles.phoneSmall}>واجهة المتجر</Text>
                </View>
                <MaterialIcons name="more-horiz" size={18} color="#FFF" />
              </View>
              {showHero ? <View style={[styles.phoneHero, { backgroundColor: primary, borderRadius: Math.max(10, radiusValue - 4) }]}><Text style={styles.phoneKicker}>مميز اليوم</Text><Text style={styles.phoneHeroTitle}>اختيارات جديدة بانتظارك</Text><View style={styles.phoneHeroButton}><Text style={styles.phoneHeroButtonText}>تسوّق الآن</Text></View></View> : null}
              {showCategories ? <View style={styles.phoneRow}>{["الكل", "ملابس", "أجهزة"].map((label, index) => <View key={label} style={styles.phoneChip}><View style={[styles.phoneChipDot, { backgroundColor: index === 0 ? primary : "#E2E4E8" }]} /><Text style={styles.phoneChipText}>{label}</Text></View>)}</View> : null}
              {showProducts ? <View style={styles.phoneGrid}>{[0, 1].map((item) => <View key={item} style={[styles.phoneProduct, { borderRadius: Math.max(8, radiusValue - 6) }]}><View style={[styles.phoneProductImage, { backgroundColor: item === 0 ? `${primary}20` : "#EFF1F4" }]} /><Text style={styles.phoneProductTitle}>{item === 0 ? "منتج مميز" : "اختيار جديد"}</Text><Text style={[styles.phoneProductPrice, { color: primary }]}>{item === 0 ? "12,500 ر.ي" : "8,900 ر.ي"}</Text></View>)}</View> : null}
            </View>
          </View>
        </View>

        <View style={styles.statsRow}>
          <Stat icon="palette" title="الهوية" value="مخصصة" subtitle="ألوان المتجر" primary={primary} />
          <Stat icon="view-quilt" title="الأقسام" value={`${[showHero, showCategories, showFlashSale, showProducts].filter(Boolean).length}/4`} subtitle="مفعلة الآن" primary={primary} />
          <Stat icon="language" title="الاتجاه" value="RTL" subtitle="واجهة عربية" primary={primary} />
        </View>

        <SectionHeader icon="palette" title="لوحات هوية جاهزة" description="اختر نمطًا متوازنًا بنقرة واحدة" />
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.paletteRow}>
          {PALETTES.map((palette) => {
            const active = selectedPalette === palette.id;
            return <TouchableOpacity key={palette.id} style={[styles.paletteCard, active && { borderColor: palette.primary, shadowColor: palette.primary }]} onPress={() => applyPalette(palette)}><View style={styles.paletteVisual}><View style={[styles.paletteMain, { backgroundColor: palette.primary }]} /><View style={[styles.paletteLight, { backgroundColor: palette.background }]} /></View><View style={styles.paletteBottom}><Text style={styles.paletteName}>{palette.name}</Text>{active ? <MaterialIcons name="check-circle" size={18} color={palette.primary} /> : <MaterialIcons name="radio-button-unchecked" size={18} color="#B7BBC2" />}</View></TouchableOpacity>;
          })}
        </ScrollView>

        <SectionHeader icon="format-color-fill" title="ألوان الهوية" description="اللون الرئيسي والخلفية والنتيجة قبل الحفظ" />
        <View style={styles.card}>
          <ColorField title="اللون الرئيسي" hint="الأزرار والعناصر التفاعلية" value={primary} onChangeText={setPrimary} />
          <ColorField title="خلفية الواجهة" hint="المساحات خلف المنتجات والأقسام" value={background} onChangeText={setBackground} last />
          <View style={styles.colorPreviewStrip}><View style={[styles.previewPart, { backgroundColor: primary }]}><Text style={styles.previewPartText}>الهوية</Text></View><View style={[styles.previewPart, { backgroundColor: background }]}><Text style={styles.previewPartTextDark}>الخلفية</Text></View><View style={[styles.previewPart, { backgroundColor: "#FFFFFF" }]}><Text style={styles.previewPartTextDark}>البطاقات</Text></View></View>
        </View>

        <SectionHeader icon="view-quilt" title="مكونات الواجهة" description="حدد ما تريد أن يراه العميل في الصفحة الرئيسية" />
        <View style={styles.card}>
          <DesignOption icon="image" title="الرئيسية والبنرات" description="عرض رئيسي وصور وعروض جذابة" value={showHero} onChange={setShowHero} primary={primary} />
          <DesignOption icon="category" title="الفئات" description="وصول سريع إلى أقسام المنتجات" value={showCategories} onChange={setShowCategories} primary={primary} />
          <DesignOption icon="local-offer" title="العروض السريعة" description="إبراز الحملات والعروض الحالية" value={showFlashSale} onChange={setShowFlashSale} primary={primary} />
          <DesignOption icon="grid-view" title="شبكة المنتجات" description="عرض المنتجات الأساسية في الواجهة" value={showProducts} onChange={setShowProducts} primary={primary} last />
        </View>

        <SectionHeader icon="rounded-corner" title="نمط البطاقات" description="اختر درجة نعومة الحواف" />
        <View style={styles.card}>
          <View style={styles.radiusHeader}><View style={{ flex: 1, alignItems: "flex-end" }}><Text style={styles.optionTitle}>زوايا البطاقات</Text><Text style={styles.optionDescription}>يظهر تأثيرها في البطاقات والأقسام</Text></View><View style={[styles.radiusValue, { borderColor: `${primary}45` }]}><Text style={[styles.radiusNumber, { color: primary }]}>{radiusValue}</Text><Text style={styles.radiusUnit}>px</Text></View></View>
          <View style={styles.radiusButtons}>{[10, 14, 18, 22, 26].map((value) => <TouchableOpacity key={value} onPress={() => setRadius(String(value))} style={[styles.radiusButton, radiusValue === value && { backgroundColor: primary, borderColor: primary }]}><Text style={[styles.radiusButtonText, radiusValue === value && { color: "#FFF" }]}>{value}</Text></TouchableOpacity>)}</View>
        </View>

        <View style={[styles.tip, { borderColor: `${primary}35`, backgroundColor: `${primary}09` }]}>
          <View style={[styles.tipIcon, { backgroundColor: `${primary}16` }]}><MaterialIcons name="tips-and-updates" size={20} color={primary} /></View>
          <View style={{ flex: 1, alignItems: "flex-end" }}><Text style={styles.tipTitle}>تحتاج تحكمًا أكبر؟</Text><Text style={styles.tipText}>افتح محرر الأقسام لإضافة وحذف وترتيب البنرات والفئات والصور ومحتوى الواجهة بالكامل.</Text></View>
          <TouchableOpacity onPress={() => router.push("/vendor/storefront" as never)}><MaterialIcons name="arrow-back-ios" size={16} color={primary} /></TouchableOpacity>
        </View>

        <TouchableOpacity disabled={saving} style={[styles.bottomButton, { backgroundColor: primary }]} onPress={save}>{saving ? <ActivityIndicator color="#FFF" /> : <><MaterialIcons name="check" size={20} color="#FFF" /><Text style={styles.bottomButtonText}>حفظ ونشر التغييرات</Text></>}</TouchableOpacity>
        <Text style={styles.footerNote}>واجهة RTL · محفوظة عبر واجهة Django الحالية · لا تحتاج Migration جديدة</Text>
      </ScrollView>
    </ScreenContainer>
  );
}

function Stat({ icon, title, value, subtitle, primary }: { icon: React.ComponentProps<typeof MaterialIcons>["name"]; title: string; value: string; subtitle: string; primary: string }) {
  return <View style={styles.stat}><View style={[styles.statIcon, { backgroundColor: `${primary}12` }]}><MaterialIcons name={icon} size={18} color={primary} /></View><Text style={styles.statLabel}>{title}</Text><Text style={styles.statValue}>{value}</Text><Text style={styles.statSub}>{subtitle}</Text></View>;
}

function SectionHeader({ icon, title, description }: { icon: React.ComponentProps<typeof MaterialIcons>["name"]; title: string; description: string }) {
  return <View style={styles.sectionHeader}><View style={styles.sectionIcon}><MaterialIcons name={icon} size={18} color="#17191F" /></View><View style={{ flex: 1, alignItems: "flex-end" }}><Text style={styles.sectionTitle}>{title}</Text><Text style={styles.sectionDescription}>{description}</Text></View></View>;
}

function ColorField({ title, hint, value, onChangeText, last = false }: { title: string; hint: string; value: string; onChangeText: (value: string) => void; last?: boolean }) {
  return <View style={[styles.colorField, !last && styles.fieldBorder]}><View style={{ flex: 1, alignItems: "flex-end" }}><Text style={styles.optionTitle}>{title}</Text><Text style={styles.optionDescription}>{hint}</Text></View><View style={styles.colorInputWrap}><View style={[styles.colorDot, { backgroundColor: validHex(value) ? value : "#D4D7DC" }]} /><TextInput value={value} onChangeText={onChangeText} placeholder="#E60023" style={styles.colorInput} autoCapitalize="characters" maxLength={7} textAlign="left" /></View></View>;
}

function DesignOption({ icon, title, description, value, onChange, primary, last = false }: { icon: React.ComponentProps<typeof MaterialIcons>["name"]; title: string; description: string; value: boolean; onChange: (value: boolean) => void; primary: string; last?: boolean }) {
  return <View style={[styles.designOption, !last && styles.fieldBorder]}><Switch value={value} onValueChange={onChange} trackColor={{ false: "#D7DADF", true: `${primary}70` }} thumbColor={value ? primary : "#FFF"} /><View style={[styles.designIcon, { backgroundColor: `${primary}10` }]}><MaterialIcons name={icon} size={19} color={primary} /></View><View style={{ flex: 1, alignItems: "flex-end" }}><Text style={styles.optionTitle}>{title}</Text><Text style={styles.optionDescription}>{description}</Text></View></View>;
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: "#F4F6F8" },
  header: { minHeight: 76, paddingHorizontal: 14, backgroundColor: "#FFF", borderBottomWidth: 1, borderBottomColor: "#E8EAEE", flexDirection: "row", alignItems: "center", gap: 10 },
  headerIcon: { width: 42, height: 42, borderRadius: 13, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  headerCenter: { flex: 1, alignItems: "flex-end" },
  headerTitle: { fontSize: 18, fontWeight: "900", color: "#13151A" },
  headerSub: { fontSize: 10, color: "#7D828B", marginTop: 4, textAlign: "right" },
  headerPreview: { minWidth: 78, height: 38, borderRadius: 12, borderWidth: 1, borderColor: "#E7E8EB", backgroundColor: "#FFF", paddingHorizontal: 9, flexDirection: "row-reverse", alignItems: "center", justifyContent: "center", gap: 5 },
  headerPreviewText: { fontSize: 10, fontWeight: "900" },
  content: { width: "100%", maxWidth: 1080, alignSelf: "center", padding: 13, paddingBottom: 90 },
  heroBanner: { minHeight: 360, borderRadius: 24, backgroundColor: "#17191F", overflow: "hidden", flexDirection: "row-reverse", padding: 18, marginBottom: 12 },
  heroOrb: { position: "absolute", width: 250, height: 250, borderRadius: 125, opacity: 0.12, left: -60, top: -55 },
  heroCopy: { flex: 1, alignItems: "flex-end", justifyContent: "center", paddingRight: 10 },
  eyebrow: { flexDirection: "row-reverse", alignItems: "center", gap: 5, paddingHorizontal: 9, paddingVertical: 6, borderRadius: 99, backgroundColor: "#FFF", alignSelf: "flex-end", marginBottom: 12 },
  eyebrowText: { fontSize: 9, fontWeight: "900" },
  heroTitle: { color: "#FFF", fontSize: 27, lineHeight: 37, fontWeight: "900", textAlign: "right", maxWidth: 570 },
  heroDescription: { color: "#C8CBD1", fontSize: 11, lineHeight: 19, textAlign: "right", maxWidth: 570, marginTop: 9 },
  heroActions: { flexDirection: "row-reverse", gap: 9, marginTop: 18 },
  primaryAction: { minHeight: 44, paddingHorizontal: 15, borderRadius: 13, flexDirection: "row-reverse", alignItems: "center", justifyContent: "center", gap: 7 },
  primaryActionText: { color: "#FFF", fontSize: 11, fontWeight: "900" },
  secondaryAction: { minHeight: 44, paddingHorizontal: 14, borderRadius: 13, backgroundColor: "#FFF", flexDirection: "row-reverse", alignItems: "center", justifyContent: "center", gap: 7 },
  secondaryActionText: { color: "#15171C", fontSize: 11, fontWeight: "900" },
  previewWrap: { width: 194, alignItems: "center", justifyContent: "center" },
  phone: { width: 164, minHeight: 305, backgroundColor: "#FFF", padding: 7, borderWidth: 2, borderColor: "#31333A", shadowColor: "#000", shadowOpacity: 0.22, shadowRadius: 20, shadowOffset: { width: 0, height: 10 }, elevation: 8, overflow: "hidden" },
  phoneTop: { minHeight: 42, borderRadius: 13, paddingHorizontal: 8, flexDirection: "row-reverse", alignItems: "center", gap: 6 },
  phoneLogo: { width: 28, height: 28, borderRadius: 9, backgroundColor: "#FFF", alignItems: "center", justifyContent: "center" },
  phoneName: { color: "#FFF", fontSize: 9, fontWeight: "900", textAlign: "right" },
  phoneSmall: { color: "#EDEEF0", fontSize: 7, marginTop: 2, textAlign: "right" },
  phoneHero: { minHeight: 86, marginTop: 7, padding: 10, justifyContent: "center", overflow: "hidden" },
  phoneKicker: { color: "#FFF", fontSize: 7, fontWeight: "900", textAlign: "right" },
  phoneHeroTitle: { color: "#FFF", fontSize: 11, fontWeight: "900", textAlign: "right", marginTop: 3 },
  phoneHeroButton: { backgroundColor: "#FFF", borderRadius: 99, paddingHorizontal: 7, paddingVertical: 4, alignSelf: "flex-end", marginTop: 7 },
  phoneHeroButtonText: { color: "#222", fontSize: 7, fontWeight: "900" },
  phoneRow: { flexDirection: "row-reverse", gap: 5, paddingVertical: 8 },
  phoneChip: { flex: 1, alignItems: "center", gap: 3 },
  phoneChipDot: { width: 20, height: 20, borderRadius: 10 },
  phoneChipText: { fontSize: 6.5, color: "#464A52", fontWeight: "800" },
  phoneGrid: { flexDirection: "row-reverse", gap: 5 },
  phoneProduct: { flex: 1, backgroundColor: "#FFF", borderWidth: 1, borderColor: "#ECEEF1", padding: 4 },
  phoneProductImage: { height: 55, borderRadius: 7 },
  phoneProductTitle: { fontSize: 6.5, color: "#24272D", fontWeight: "800", textAlign: "right", marginTop: 4 },
  phoneProductPrice: { fontSize: 6.5, fontWeight: "900", textAlign: "right", marginTop: 3 },
  statsRow: { flexDirection: "row-reverse", gap: 9, marginBottom: 16 },
  stat: { flex: 1, backgroundColor: "#FFF", borderRadius: 16, padding: 11, borderWidth: 1, borderColor: "#EAECF0", alignItems: "flex-end", minHeight: 104 },
  statIcon: { width: 34, height: 34, borderRadius: 11, alignItems: "center", justifyContent: "center", alignSelf: "flex-start" },
  statLabel: { fontSize: 9, color: "#858A93", marginTop: 4 },
  statValue: { fontSize: 16, color: "#17191F", fontWeight: "900", marginTop: 1 },
  statSub: { fontSize: 8, color: "#9A9EA7", marginTop: 2 },
  sectionHeader: { flexDirection: "row-reverse", alignItems: "center", gap: 9, marginTop: 6, marginBottom: 9, paddingHorizontal: 2 },
  sectionIcon: { width: 38, height: 38, borderRadius: 12, backgroundColor: "#FFF", borderWidth: 1, borderColor: "#EAECF0", alignItems: "center", justifyContent: "center" },
  sectionTitle: { color: "#17191F", fontSize: 15, fontWeight: "900", textAlign: "right" },
  sectionDescription: { color: "#858A93", fontSize: 9, marginTop: 3, textAlign: "right" },
  paletteRow: { gap: 9, paddingBottom: 6, paddingHorizontal: 2 },
  paletteCard: { width: 145, backgroundColor: "#FFF", borderRadius: 16, borderWidth: 1.5, borderColor: "#E9EBEF", padding: 9, shadowOpacity: 0.04, shadowRadius: 12, shadowOffset: { width: 0, height: 5 }, elevation: 1 },
  paletteVisual: { flexDirection: "row", gap: 5, height: 64 },
  paletteMain: { flex: 2, borderRadius: 12 },
  paletteLight: { flex: 1, borderRadius: 10 },
  paletteBottom: { flexDirection: "row-reverse", alignItems: "center", justifyContent: "space-between", marginTop: 8 },
  paletteName: { fontSize: 10, fontWeight: "900", color: "#282B32" },
  card: { backgroundColor: "#FFF", borderRadius: 18, borderWidth: 1, borderColor: "#EAECF0", paddingHorizontal: 14, paddingVertical: 6, marginBottom: 14 },
  colorField: { minHeight: 72, flexDirection: "row-reverse", alignItems: "center", gap: 12 },
  fieldBorder: { borderBottomWidth: 1, borderBottomColor: "#F0F1F3" },
  colorInputWrap: { flexDirection: "row-reverse", alignItems: "center", width: 170, height: 44, backgroundColor: "#F7F8FA", borderRadius: 12, borderWidth: 1, borderColor: "#E3E5E8", paddingHorizontal: 8, gap: 8 },
  colorDot: { width: 28, height: 28, borderRadius: 9, borderWidth: 1, borderColor: "#E2E4E7" },
  colorInput: { flex: 1, paddingVertical: 0, color: "#17191F", fontSize: 12, fontWeight: "800" },
  colorPreviewStrip: { flexDirection: "row-reverse", borderRadius: 12, overflow: "hidden", height: 42, marginTop: 7, marginBottom: 9 },
  previewPart: { flex: 1, alignItems: "center", justifyContent: "center" },
  previewPartText: { color: "#FFF", fontSize: 9, fontWeight: "900" },
  previewPartTextDark: { color: "#454950", fontSize: 9, fontWeight: "900" },
  optionTitle: { color: "#202329", fontSize: 12, fontWeight: "900", textAlign: "right" },
  optionDescription: { color: "#858A93", fontSize: 9, lineHeight: 16, marginTop: 2, textAlign: "right" },
  designOption: { minHeight: 74, flexDirection: "row-reverse", alignItems: "center", gap: 11 },
  designIcon: { width: 38, height: 38, borderRadius: 12, alignItems: "center", justifyContent: "center" },
  radiusHeader: { minHeight: 76, flexDirection: "row-reverse", justifyContent: "space-between", alignItems: "center" },
  radiusValue: { minWidth: 72, height: 48, borderRadius: 14, backgroundColor: "#F8F9FA", borderWidth: 1, alignItems: "center", justifyContent: "center", flexDirection: "row-reverse", gap: 3 },
  radiusNumber: { fontSize: 18, fontWeight: "900" },
  radiusUnit: { color: "#858A93", fontSize: 9, fontWeight: "800" },
  radiusButtons: { flexDirection: "row-reverse", gap: 7, paddingBottom: 10 },
  radiusButton: { minWidth: 45, height: 38, paddingHorizontal: 9, borderRadius: 11, borderWidth: 1, borderColor: "#E4E6E9", backgroundColor: "#F8F9FA", alignItems: "center", justifyContent: "center" },
  radiusButtonText: { color: "#4F535B", fontSize: 10, fontWeight: "900" },
  tip: { minHeight: 88, borderRadius: 18, borderWidth: 1, padding: 13, flexDirection: "row-reverse", alignItems: "center", gap: 10, marginBottom: 14 },
  tipIcon: { width: 38, height: 38, borderRadius: 12, alignItems: "center", justifyContent: "center" },
  tipTitle: { color: "#23262C", fontSize: 11, fontWeight: "900", textAlign: "right" },
  tipText: { color: "#6E737C", fontSize: 9, lineHeight: 17, textAlign: "right", marginTop: 3 },
  bottomButton: { minHeight: 54, borderRadius: 16, alignItems: "center", justifyContent: "center", flexDirection: "row-reverse", gap: 8, marginTop: 3 },
  bottomButtonText: { color: "#FFF", fontSize: 13, fontWeight: "900" },
  footerNote: { color: "#92969E", fontSize: 8.5, lineHeight: 15, textAlign: "center", marginTop: 8 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 8 },
  loadingText: { color: "#737882", fontSize: 10, fontWeight: "700" },
});