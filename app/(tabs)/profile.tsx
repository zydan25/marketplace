import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { Alert, Image, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import { useEffect, useState } from "react";
import { ScreenContainer } from "@/components/screen-container";
import { useAuth } from "@/hooks/use-auth";
import { djangoApi } from "@/lib/django-api";

const later = (title: string) => Alert.alert(title, "ستتوفر هذه الميزة ضمن حسابك قريبًا.");

export default function ProfileScreen() {
  const { user, isAuthenticated, logout } = useAuth();
  const [walletBalance, setWalletBalance] = useState("0");
  useEffect(() => { if (user?.role === "vendor") router.replace("/vendor" as never); }, [user?.role]);
  useEffect(() => {
    if (!isAuthenticated || user?.role !== "customer") return;
    djangoApi<any>("/api/wallets/").then((response) => setWalletBalance(String(response.results?.[0]?.balance ?? response.balance ?? "0"))).catch(() => undefined);
  }, [isAuthenticated, user?.role]);
  if (user?.role === "vendor") return null;
  if (!isAuthenticated) return <Guest />;
  const name = user?.name?.trim() || "شبيك";
  const admin = user?.role === "admin";
  return (
    <ScreenContainer edges={["top", "left", "right"]} className="bg-[#F6F6F7]">
      <ScrollView style={s.scroll} showsVerticalScrollIndicator={false} contentContainerStyle={s.content}>
        <View style={s.head}>
          <View style={s.headActions}><TouchableOpacity style={s.iconButton} onPress={() => router.push("/settings" as never)}><MaterialIcons name="settings" size={22} color="#111" /></TouchableOpacity><TouchableOpacity style={s.iconButton} onPress={() => later("رمز حسابي")}><MaterialIcons name="qr-code-scanner" size={22} color="#111" /></TouchableOpacity></View>
          <View style={s.identity}><View style={s.avatar}><Text style={s.avatarText}>{name.slice(0, 1)}</Text></View><View><Text style={s.name}>{name}</Text><Text style={s.personal}>حسابي الشخصي · <MaterialIcons name="edit" size={12} color="#777" /></Text></View></View>
        </View>
        <View style={s.wallet}>
          <Metric icon="local-offer" label="الكوبونات" value="0" /><Metric icon="stars" label="النقاط" value={String(user?.points_balance ?? 0)} /><Metric icon="account-balance-wallet" label="المحفظة" value={`${walletBalance} ر.ي`} onPress={() => router.push("/customer-reports" as never)} /><Metric icon="card-giftcard" label="بطاقة هدية" value="" />
          <View style={s.coupon}><MaterialIcons name="local-offer" color="#E60023" size={19} /><Text style={s.couponText}>ستظهر هنا الكوبونات والعروض المتاحة لحسابك.</Text></View>
        </View>
        <Panel title="طلباتي" action="عرض الكل" onAction={() => router.push("/orders" as never)}>
          <Action icon="credit-card" label="غير مدفوع" /><Action icon="inventory-2" label="قيد التجهيز" /><Action icon="local-shipping" label="تم الشحن" /><Action icon="rate-review" label="بانتظار التقييم" />
        </Panel>
        <View style={s.panel}>
          <Action icon="support-agent" label="تواصل معنا" onPress={() => router.push("/support" as never)} />
          <Action icon="card-giftcard" label="إرسال هدية" onPress={() => router.push("/extra-features" as never)} />
          <Action icon="analytics" label="تقارير الحساب" onPress={() => router.push("/customer-reports" as never)} />
          <Action icon="storefront" label="التجار" onPress={() => router.push("/vendors" as never)} />
          <Action icon="verified-user" label="السياسة" />
          <Action icon="share" label="دعوة" onPress={() => router.push("/invite" as never)} />
        </View>
        <View style={s.metrics}><MetricStat label="المتابعات" value="0" /><MetricStat label="المنتجات المحفوظة" value="0" /><MetricStat label="المفضلة" value="0" /></View>
        <View style={s.favorites}><MaterialIcons name="favorite-border" size={34} color="#E60023" /><Text style={s.favTitle}>ستظهر منتجاتك المفضلة هنا</Text><Text style={s.favText}>احفظ المنتجات التي تعجبك لتعود إليها بسرعة لاحقًا.</Text></View>
        {admin ? <TouchableOpacity style={s.admin} onPress={() => router.push("/admin" as never)}><MaterialIcons name="admin-panel-settings" size={22} color="#F0B800" /><Text style={s.adminText}>لوحة الإدارة</Text></TouchableOpacity> : null}
        <TouchableOpacity style={s.logout} onPress={logout}><MaterialIcons name="logout" size={20} color="#BB3F46" /><Text style={s.logoutText}>تسجيل الخروج</Text></TouchableOpacity>
      </ScrollView>
    </ScreenContainer>
  );
}

function Guest() { return <ScreenContainer edges={["top", "bottom", "left", "right"]} className="bg-[#FCFBF8]"><View style={s.guest}><Image source={require("@/assets/images/icon.png")} style={s.guestLogo} /><Text style={s.guestTitle}>أهلاً بك في شبيك</Text><Text style={s.guestSub}>سجل الدخول للوصول إلى طلباتك وكوبوناتك ومزايا حسابك.</Text><TouchableOpacity style={s.guestButton} onPress={() => router.push("/login" as never)}><Text style={s.guestButtonText}>تسجيل الدخول</Text></TouchableOpacity></View></ScreenContainer>; }
function Metric({ icon, label, value, onPress }: { icon: string; label: string; value: string; onPress?: () => void }) { return <TouchableOpacity style={s.walletItem} onPress={onPress || (() => later(label))}><MaterialIcons name={icon as any} size={22} color="#333" />{value ? <Text style={s.value}>{value}</Text> : null}<Text style={s.walletLabel}>{label}</Text></TouchableOpacity>; }
function MetricStat({ label, value }: { label: string; value: string }) { return <View style={s.metricStat}><Text style={s.metricValue}>{value}</Text><Text style={s.metricLabel}>{label}</Text></View>; }
function Action({ icon, label, onPress }: { icon: string; label: string; onPress?: () => void }) { return <TouchableOpacity style={s.action} onPress={onPress || (() => later(label))}><MaterialIcons name={icon as any} size={22} color="#333" /><Text style={s.actionText}>{label}</Text></TouchableOpacity>; }
function Panel({ title, action, onAction, children }: { title: string; action: string; onAction: () => void; children: React.ReactNode }) { return <View style={s.orders}><View style={s.panelTop}><TouchableOpacity onPress={onAction}><Text style={s.all}>{action} ←</Text></TouchableOpacity><Text style={s.panelTitle}>{title}</Text></View><View style={s.actions}>{children}</View></View>; }

const s = StyleSheet.create({
  scroll: { flex: 1, minHeight: 0 },
  content: { paddingBottom: 120, flexGrow: 1 },
  head: { backgroundColor: "#FFF", padding: 14, paddingTop: 16, flexDirection: "row", alignItems: "center", justifyContent: "space-between", borderBottomWidth: 1, borderColor: "#F0F0F0" },
  headActions: { flexDirection: "row-reverse", gap: 5 },
  iconButton: { width: 38, height: 38, borderRadius: 19, alignItems: "center", justifyContent: "center", backgroundColor: "#F7F7F7" },
  identity: { flexDirection: "row-reverse", gap: 10, alignItems: "center" },
  avatar: { width: 46, height: 46, borderRadius: 23, backgroundColor: "#111", alignItems: "center", justifyContent: "center" },
  avatarText: { fontSize: 19, fontWeight: "900", color: "#FFF" },
  name: { fontSize: 16, fontWeight: "900", textAlign: "right", color: "#111" },
  personal: { color: "#777", fontSize: 10, textAlign: "right", marginTop: 2 },
  wallet: { margin: 12, backgroundColor: "#FFF", flexDirection: "row-reverse", flexWrap: "wrap", borderRadius: 16, paddingTop: 15, borderWidth: 1, borderColor: "#ECECEC" },
  walletItem: { width: "25%", minWidth: 70, alignItems: "center", minHeight: 66 },
  value: { fontSize: 13, fontWeight: "900", color: "#111", marginTop: 3, maxWidth: 82, textAlign: "center" },
  walletLabel: { fontSize: 9, color: "#555", marginTop: 3, textAlign: "center" },
  coupon: { width: "100%", borderTopWidth: 1, borderColor: "#F3F3F3", padding: 11, flexDirection: "row-reverse", alignItems: "center", gap: 7 },
  couponText: { fontSize: 10, color: "#794F1A", flex: 1, textAlign: "right" },
  orders: { marginHorizontal: 12, backgroundColor: "#FFF", borderRadius: 16, borderWidth: 1, borderColor: "#ECECEC" },
  panel: { marginHorizontal: 12, marginTop: 12, backgroundColor: "#FFF", paddingVertical: 15, flexDirection: "row-reverse", flexWrap: "wrap", borderRadius: 16, borderWidth: 1, borderColor: "#ECECEC" },
  panelTop: { paddingHorizontal: 15, paddingTop: 14, width: "100%", flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  panelTitle: { fontSize: 15, fontWeight: "900", color: "#111" },
  all: { color: "#777", fontSize: 11 },
  actions: { flexDirection: "row-reverse", width: "100%", paddingTop: 13 },
  action: { flex: 1, minWidth: "23%", alignItems: "center", paddingHorizontal: 3 },
  actionText: { fontSize: 9, color: "#555", textAlign: "center", marginTop: 6, lineHeight: 15 },
  metrics: { margin: 12, backgroundColor: "#FFF", borderRadius: 16, paddingVertical: 15, flexDirection: "row-reverse", borderWidth: 1, borderColor: "#ECECEC" },
  metricStat: { flex: 1, alignItems: "center" },
  metricValue: { fontSize: 18, fontWeight: "900", color: "#111" },
  metricLabel: { fontSize: 9, color: "#777", marginTop: 3, textAlign: "center" },
  favorites: { margin: 12, padding: 24, backgroundColor: "#FFF", borderRadius: 16, alignItems: "center", borderStyle: "dashed", borderWidth: 1, borderColor: "#DDD" },
  favTitle: { fontSize: 14, fontWeight: "900", color: "#111", marginTop: 8 },
  favText: { color: "#777", fontSize: 11, marginTop: 5, textAlign: "center", lineHeight: 18 },
  admin: { height: 46, marginHorizontal: 12, marginTop: 12, backgroundColor: "#111", borderRadius: 13, flexDirection: "row-reverse", justifyContent: "center", alignItems: "center", gap: 7 },
  adminText: { color: "#FFF", fontSize: 13, fontWeight: "900" },
  logout: { alignSelf: "center", padding: 15, flexDirection: "row-reverse", gap: 6, marginTop: 4 },
  logoutText: { color: "#E60023", fontSize: 12, fontWeight: "700" },
  guest: { flex: 1, justifyContent: "center", alignItems: "center", paddingHorizontal: 28 },
  guestLogo: { width: 76, height: 76, borderRadius: 19, marginBottom: 22 },
  guestTitle: { fontSize: 21, fontWeight: "900", color: "#111", textAlign: "center" },
  guestSub: { fontSize: 12, color: "#777", textAlign: "center", lineHeight: 21, marginTop: 8 },
  guestButton: { marginTop: 28, width: "100%", maxWidth: 300, height: 46, borderRadius: 13, backgroundColor: "#111", alignItems: "center", justifyContent: "center" },
  guestButtonText: { color: "#FFF", fontSize: 14, fontWeight: "800" },
});
