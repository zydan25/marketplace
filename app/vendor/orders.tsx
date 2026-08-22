import { useEffect, useState } from "react";
import { Alert, ActivityIndicator, FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ScreenContainer } from "@/components/screen-container";
import { djangoApi } from "@/lib/django-api";

type Order = { id: number; order_number: string; status: string; total: string; currency: string; created_at: string; customer?: { phone?: string } };
const statuses = ["pending", "processing", "shipped", "delivered", "cancelled"];

export default function VendorOrdersScreen() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState<number | null>(null);

  async function load() {
    try {
      const result = await djangoApi<{ results?: Order[] }>("/api/orders/");
      setOrders(result.results ?? []);
    } catch (error) {
      Alert.alert("تعذر تحميل الطلبات", error instanceof Error ? error.message : "حاولي مجددًا.");
    } finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  async function updateStatus(order: Order, status: string) {
    setUpdating(order.id);
    try {
      await djangoApi(`/api/orders/${order.id}/update_status/`, { method: "POST", body: JSON.stringify({ status }) });
      setOrders(current => current.map(item => item.id === order.id ? { ...item, status } : item));
    } catch (error) {
      Alert.alert("تعذر تحديث الطلب", error instanceof Error ? error.message : "حاولي مجددًا.");
    } finally { setUpdating(null); }
  }

  return <ScreenContainer className="bg-[#F8F9FA]" edges={["top", "bottom", "left", "right"]}>
    <View style={styles.header}><TouchableOpacity onPress={() => router.back()}><MaterialIcons name="arrow-forward" size={24} color="#111" /></TouchableOpacity><Text style={styles.title}>إدارة الطلبات</Text><TouchableOpacity onPress={load}><MaterialIcons name="refresh" size={22} color="#E60023" /></TouchableOpacity></View>
    {loading ? <View style={styles.center}><ActivityIndicator color="#E60023" /><Text style={styles.muted}>جارٍ تحميل الطلبات...</Text></View> : <FlatList style={{ flex: 1 }} data={orders} keyExtractor={item => String(item.id)} contentContainerStyle={styles.list} ListEmptyComponent={<View style={styles.empty}><MaterialIcons name="shopping-bag" size={45} color="#DDD" /><Text style={styles.muted}>لا توجد طلبات لمتجرك.</Text></View>} renderItem={({ item }) => <View style={styles.card}><View style={styles.cardHead}><View><Text style={styles.amount}>{item.total} {item.currency}</Text><Text style={styles.date}>{new Date(item.created_at).toLocaleDateString("ar-YE")}</Text></View><View style={styles.orderCopy}><Text style={styles.number}>#{item.order_number}</Text><Text style={styles.customer}>{item.customer?.phone || "عميل"}</Text></View></View><Text style={styles.label}>تحديث الحالة</Text><View style={styles.statuses}>{statuses.map(status => <TouchableOpacity key={status} disabled={updating === item.id} onPress={() => updateStatus(item, status)} style={[styles.statusBtn, item.status === status && styles.statusActive]}><Text style={[styles.statusText, item.status === status && styles.statusTextActive]}>{translate(status)}</Text></TouchableOpacity>)}</View></View>} />}
  </ScreenContainer>;
}

function translate(status: string) { return ({ pending: "جديد", processing: "تجهيز", shipped: "شحن", delivered: "تم", cancelled: "ملغى" } as Record<string, string>)[status] || status; }
const styles = StyleSheet.create({ header: { height: 60, paddingHorizontal: 16, backgroundColor: "#FFF", flexDirection: "row", justifyContent: "space-between", alignItems: "center", borderBottomWidth: 1, borderColor: "#EEE" }, title: { fontSize: 19, fontWeight: "900", color: "#111" }, list: { padding: 12, paddingBottom: 180 }, card: { backgroundColor: "#FFF", borderRadius: 12, padding: 15, marginBottom: 10, borderWidth: 1, borderColor: "#F0F0F0" }, cardHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" }, orderCopy: { alignItems: "flex-end" }, number: { fontSize: 15, fontWeight: "900", color: "#111" }, customer: { fontSize: 11, color: "#777", marginTop: 4 }, amount: { color: "#E60023", fontSize: 15, fontWeight: "900" }, date: { color: "#999", fontSize: 10, marginTop: 4 }, label: { color: "#777", fontSize: 11, textAlign: "right", marginTop: 14, marginBottom: 7 }, statuses: { flexDirection: "row-reverse", gap: 5, flexWrap: "wrap" }, statusBtn: { borderWidth: 1, borderColor: "#DDD", paddingHorizontal: 9, paddingVertical: 7, borderRadius: 6 }, statusActive: { backgroundColor: "#111", borderColor: "#111" }, statusText: { color: "#666", fontSize: 10, fontWeight: "700" }, statusTextActive: { color: "#FFF" }, center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 10 }, muted: { color: "#777", fontSize: 13 }, empty: { alignItems: "center", paddingTop: 70, gap: 12 } });
