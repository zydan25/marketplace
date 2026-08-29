import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ActivityIndicator, FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import { useEffect, useState } from "react";

import { formatYER } from "@/lib/catalog";
import { ScreenContainer } from "@/components/screen-container";
import { useAuth } from "@/hooks/use-auth";
import { getMyOrders, type StoreOrder } from "@/lib/order-api";

const progress: Record<string, number> = { pending: 20, confirmed: 35, processing: 52, partially_fulfilled: 68, shipped: 80, delivered: 100, cancelled: 100, refunded: 100, paid_shipping: 80 };

export default function OrdersScreen() {
  const { isAuthenticated } = useAuth();
  const [orders, setOrders] = useState<StoreOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = async () => { try { setLoading(true); setError(""); setOrders(await getMyOrders()); } catch (e) { setError(e instanceof Error ? e.message : "تعذر تحميل الطلبات."); } finally { setLoading(false); } };
  useEffect(() => { if (isAuthenticated) load(); else setLoading(false); }, [isAuthenticated]);

  if (!isAuthenticated) return <ScreenContainer edges={["top", "bottom", "left", "right"]} className="bg-white"><View style={styles.empty}><MaterialIcons name="lock-outline" size={38} color="#E60023" /><Text style={styles.emptyTitle}>سجل الدخول لرؤية طلباتك</Text><TouchableOpacity style={styles.login} onPress={() => router.push("/login" as never)}><Text style={styles.loginText}>تسجيل الدخول</Text></TouchableOpacity></View></ScreenContainer>;

  return <ScreenContainer edges={["top", "left", "right", "bottom"]} className="bg-[#F6F6F6]"><View style={styles.header}><TouchableOpacity onPress={() => router.back()} style={styles.headerButton}><MaterialIcons name="arrow-forward" size={23} color="#171717" /></TouchableOpacity><Text style={styles.title}>طلباتي</Text><TouchableOpacity onPress={load} style={styles.headerButton}><MaterialIcons name="refresh" size={20} color="#171717" /></TouchableOpacity></View><FlatList data={orders} keyExtractor={(item) => String(item.id)} showsVerticalScrollIndicator={false} contentContainerStyle={styles.list} refreshing={loading} onRefresh={load} renderItem={({ item }) => <TouchableOpacity style={styles.order} activeOpacity={0.88} onPress={() => router.push(`/order/${item.id}` as never)}><View style={styles.top}><View style={styles.statusPill}><Text style={styles.status}>{item.statusLabel}</Text></View><Text style={styles.number}>#{item.orderCode}</Text></View><View style={styles.divider} /><View style={styles.bottom}><Text style={styles.total}>{formatYER(item.totalAmount)}</Text><Text style={styles.date}>{item.items.length} منتج · {new Date(item.createdAt).toLocaleDateString("ar-YE")}</Text></View><View style={styles.track}><View style={[styles.trackActive, { width: `${progress[item.status] ?? 20}%` }, (item.status === "delivered" || item.status === "refunded") && styles.trackDone, item.status === "cancelled" && styles.trackCancelled]} /></View><View style={styles.detailHint}><MaterialIcons name="arrow-back" size={14} color="#777" /><Text style={styles.detailHintText}>عرض تفاصيل الطلب والمحادثة</Text></View></TouchableOpacity>} ListHeaderComponent={<View style={styles.banner}><MaterialIcons name="receipt-long" size={24} color="#E60023" /><View style={styles.bannerCopy}><Text style={styles.bannerTitle}>تابع طلباتك بسهولة</Text><Text style={styles.bannerText}>اضغط على الطلب لعرض التفاصيل، الحالة، المنتجات، ثم افتح المحادثة عند الحاجة.</Text></View></View>} ListEmptyComponent={loading ? <ActivityIndicator color="#E60023" style={{ marginTop: 35 }} /> : error ? <View style={styles.empty}><MaterialIcons name="error-outline" size={40} color="#E60023" /><Text style={styles.emptyText}>{error}</Text><TouchableOpacity style={styles.retry} onPress={load}><Text style={styles.retryText}>إعادة المحاولة</Text></TouchableOpacity></View> : <View style={styles.empty}><MaterialIcons name="receipt-long" size={42} color="#9D9D9D" /><Text style={styles.emptyTitle}>لا توجد طلبات بعد</Text><Text style={styles.emptyText}>ابدأ التسوق ثم عد إلى هنا لمتابعة طلباتك.</Text></View>} /></ScreenContainer>;
}

const styles = StyleSheet.create({
  header: { height: 58, backgroundColor: "#FFF", paddingHorizontal: 12, flexDirection: "row", alignItems: "center", justifyContent: "space-between", borderBottomWidth: 1, borderColor: "#EAEAEA" },
  headerButton: { width: 38, height: 38, borderRadius: 19, backgroundColor: "#F6F6F6", alignItems: "center", justifyContent: "center" },
  title: { color: "#171717", fontWeight: "900", fontSize: 16 },
  list: { padding: 12, paddingBottom: 120 },
  banner: { backgroundColor: "#FDECEF", padding: 13, borderRadius: 12, flexDirection: "row-reverse", gap: 10, alignItems: "center", marginBottom: 10 },
  bannerCopy: { flex: 1, alignItems: "flex-end" }, bannerTitle: { color: "#57111D", fontSize: 13, fontWeight: "900" }, bannerText: { color: "#8A5560", fontSize: 10, marginTop: 3, textAlign: "right", lineHeight: 16 },
  order: { backgroundColor: "#FFF", padding: 14, marginBottom: 9, borderRadius: 14, borderWidth: 1, borderColor: "#ECECEC" },
  top: { flexDirection: "row-reverse", justifyContent: "space-between", alignItems: "center" }, statusPill: { backgroundColor: "#F7F7F7", paddingHorizontal: 8, paddingVertical: 5, borderRadius: 16 }, status: { color: "#333", fontSize: 10, fontWeight: "900" }, number: { color: "#222", fontSize: 12, fontWeight: "800" }, divider: { height: 1, backgroundColor: "#EDEDED", marginVertical: 11 }, bottom: { flexDirection: "row-reverse", justifyContent: "space-between" }, total: { color: "#171717", fontSize: 14, fontWeight: "900" }, date: { color: "#777", fontSize: 10 }, track: { height: 4, borderRadius: 4, backgroundColor: "#ECECEC", marginTop: 12, width: "100%", overflow: "hidden" }, trackActive: { height: "100%", backgroundColor: "#E60023", borderRadius: 4 }, trackDone: { backgroundColor: "#168451" }, trackCancelled: { backgroundColor: "#777" },
  detailHint: { marginTop: 10, flexDirection: "row-reverse", alignItems: "center", justifyContent: "center", gap: 4 }, detailHintText: { color: "#777", fontSize: 9, fontWeight: "800" },
  empty: { flex: 1, alignItems: "center", justifyContent: "center", padding: 34, gap: 9 }, emptyTitle: { color: "#313131", fontSize: 14, fontWeight: "900", textAlign: "center" }, emptyText: { color: "#777", fontSize: 11, textAlign: "center", lineHeight: 18 }, login: { backgroundColor: "#171717", paddingHorizontal: 22, paddingVertical: 12, marginTop: 4, borderRadius: 20 }, loginText: { color: "#FFF", fontWeight: "800" }, retry: { backgroundColor: "#111", paddingHorizontal: 18, paddingVertical: 10, borderRadius: 18, marginTop: 6 }, retryText: { color: "#FFF", fontWeight: "800", fontSize: 11 },
});
