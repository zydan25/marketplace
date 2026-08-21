import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { Alert, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";

import { ScreenContainer } from "@/components/screen-container";
import { useAuth } from "@/hooks/use-auth";

const sections = [
  { icon: "inventory-2", label: "الأصناف", text: "إضافة وتعديل المنتجات", route: "/admin/products" },
  { icon: "view-carousel", label: "التحكم بالشريط العلوي", text: "تبويبات وعروض وأقسام دائرية", route: "/admin/storefront" },
  { icon: "category", label: "الفئات والعروض", text: "الأقسام والبنرات" },
  { icon: "receipt-long", label: "الطلبات", text: "متابعة الطلبات والدردشات", route: "/admin/orders" },
  { icon: "notifications-active", label: "إشعارات العملاء", text: "إرسال إشعار موجه", route: "/admin/notifications" },
  { icon: "payments", label: "التحكم بالأسعار", text: "قاعدة المحافظات والتوصيل", route: "/admin/pricing" },
  { icon: "support-agent", label: "محادثات العملاء", text: "متابعة رسائل تواصل معنا", route: "/admin/support" },
  { icon: "group-add", label: "الدعوات والمكافآت", text: "تفعيل الرابط وتتبع المدعوين", route: "/admin/referrals" },
  { icon: "people-outline", label: "العملاء", text: "الكوبونات والهدايا", route: "/admin/customers" },
  { icon: "account-balance-wallet", label: "المحافظ وسندات القبض", text: "إضافة رصيد وتسجيل العمليات", route: "/admin/wallets" },
];

export default function AdminScreen() {
  const { user, isAuthenticated } = useAuth();
  if (!isAuthenticated || user?.role !== "admin") return <ScreenContainer edges={["top", "bottom", "left", "right"]} className="bg-white"><View style={styles.denied}><MaterialIcons name="lock-outline" size={38} color="#E60023" /><Text style={styles.deniedTitle}>هذه الصفحة للمدير فقط</Text><Text style={styles.deniedText}>سجّلي الدخول بحساب الإدارة للوصول إلى لوحة التحكم.</Text><TouchableOpacity style={styles.deniedButton} onPress={() => router.replace("/login" as never)}><Text style={styles.deniedButtonText}>تسجيل الدخول</Text></TouchableOpacity></View></ScreenContainer>;
  return <ScreenContainer edges={["top", "bottom", "left", "right"]} className="bg-[#F6F6F6]"><View style={styles.header}><TouchableOpacity onPress={() => router.back()}><MaterialIcons name="arrow-forward" size={24} color="#171717" /></TouchableOpacity><Text style={styles.headerTitle}>لوحة تحكم المدير</Text><View style={{ width: 24 }} /></View><View style={styles.hero}><View style={styles.heroIcon}><MaterialIcons name="admin-panel-settings" size={29} color="#FFFFFF" /></View><Text style={styles.heroTitle}>مرحبًا، {user.name}</Text><Text style={styles.heroText}>أنت الآن ضمن مركز تحكم التخفيض الصح.</Text></View><View style={styles.grid}>{sections.map((section) => <TouchableOpacity key={section.label} style={styles.card} onPress={() => "route" in section ? router.push(section.route as never) : Alert.alert(section.label, "سيتم ربط أدوات الإدارة الكاملة في المرحلة التالية.")}><MaterialIcons name={section.icon as never} size={26} color="#171717" /><Text style={styles.cardTitle}>{section.label}</Text><Text style={styles.cardText}>{section.text}</Text></TouchableOpacity>)}</View><View style={styles.secure}><MaterialIcons name="verified-user" size={20} color="#168451" /><Text style={styles.secureText}>تم التحقق من صلاحية المدير عبر الجلسة الخادمية.</Text></View></ScreenContainer>;
}

const styles = StyleSheet.create({ header: { height: 56, paddingHorizontal: 15, backgroundColor: "#FFFFFF", flexDirection: "row", justifyContent: "space-between", alignItems: "center", borderBottomWidth: 1, borderColor: "#E9E9E9" }, headerTitle: { color: "#171717", fontSize: 16, fontWeight: "900" }, hero: { backgroundColor: "#171717", padding: 20, alignItems: "flex-end" }, heroIcon: { backgroundColor: "#E60023", width: 50, height: 50, justifyContent: "center", alignItems: "center", marginBottom: 12 }, heroTitle: { color: "#FFFFFF", fontSize: 20, fontWeight: "900" }, heroText: { color: "#C5C5C5", fontSize: 11, marginTop: 4 }, grid: { flexDirection: "row-reverse", flexWrap: "wrap", gap: 10, padding: 12 }, card: { width: "48.5%", minHeight: 137, backgroundColor: "#FFFFFF", padding: 15, alignItems: "flex-end" }, cardTitle: { color: "#1E1E1E", fontSize: 14, fontWeight: "900", marginTop: 13 }, cardText: { color: "#777777", fontSize: 10, textAlign: "right", marginTop: 4 }, secure: { marginHorizontal: 12, padding: 12, backgroundColor: "#ECF8F1", flexDirection: "row-reverse", alignItems: "center", gap: 8 }, secureText: { color: "#226541", fontSize: 11, flex: 1, textAlign: "right" }, denied: { flex: 1, alignItems: "center", justifyContent: "center", padding: 30 }, deniedTitle: { color: "#171717", fontSize: 19, fontWeight: "900", marginTop: 14 }, deniedText: { color: "#777777", fontSize: 12, textAlign: "center", marginTop: 7 }, deniedButton: { backgroundColor: "#171717", paddingHorizontal: 25, paddingVertical: 13, marginTop: 20 }, deniedButtonText: { color: "#FFFFFF", fontWeight: "800", fontSize: 13 },
});
