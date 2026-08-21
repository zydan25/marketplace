import { useEffect, useState } from "react";
import { ActivityIndicator, FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ScreenContainer } from "@/components/screen-container";
import { djangoApi, djangoLogout } from "@/lib/django-api";

type Vendor = { store_name: string; status: string; commission_percent: string; settings: Record<string, unknown> };
type Product = { id: number; name: string; sku: string; effective_price: string; stock: number; is_published: boolean };
type Order = { id: number; order_number: string; status: string; total: string; currency: string };

type VendorData = { store_name: string; status: string; commission_percent: string };

export default function VendorDashboardScreen() {
  const [vendor, setVendor] = useState<VendorData | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    Promise.all([
      djangoApi<{ results?: Vendor[] }>("/api/vendors/"),
      djangoApi<{ results?: Product[] }>("/api/products/"),
      djangoApi<{ results?: Order[] }>("/api/orders/"),
    ]).then(([vendors, productPage, orderPage]) => {
      if (!active) return;
      const current = vendors.results?.[0];
      setVendor(current ? { store_name: current.store_name, status: current.status, commission_percent: current.commission_percent } : null);
      setProducts(productPage.results ?? []);
      setOrders(orderPage.results ?? []);
    }).catch(() => {
      if (active) { setProducts([]); setOrders([]); }
    }).finally(() => active && setLoading(false));
    return () => { active = false; };
  }, []);

  async function logout() {
    await djangoLogout();
    router.replace("/vendor/login" as never);
  }

  if (loading) return <ScreenContainer><View style={styles.loading}><ActivityIndicator color="#E60023" /><Text style={styles.muted}>جارٍ تحميل لوحة المتجر...</Text></View></ScreenContainer>;

  return (
    <ScreenContainer className="bg-[#F5F5F5]" edges={["top", "bottom", "left", "right"]}>
      <FlatList
        data={orders.slice(0, 5)}
        keyExtractor={(item) => String(item.id)}
        contentContainerStyle={styles.content}
        ListHeaderComponent={<>
          <View style={styles.header}>
            <TouchableOpacity onPress={logout}><MaterialIcons name="logout" size={23} color="#777" /></TouchableOpacity>
            <View style={{ flex: 1 }}><Text style={styles.title}>{vendor?.store_name ?? "متجري"}</Text><Text style={styles.muted}>لوحة التاجر · {vendor?.status === "active" ? "نشط" : "قيد المراجعة"}</Text></View>
            <View style={styles.logo}><MaterialIcons name="storefront" size={25} color="#FFF" /></View>
          </View>
          <View style={styles.metrics}>
            <Metric label="المنتجات" value={String(products.length)} icon="inventory-2" />
            <Metric label="الطلبات" value={String(orders.length)} icon="shopping-bag" />
            <Metric label="العمولة" value={`${vendor?.commission_percent ?? 0}%`} icon="percent" />
          </View>
          <View style={styles.actions}>
            <Action label="إضافة منتج" icon="add-box" onPress={() => router.push("/vendor/products" as never)} />
            <Action label="تصميم المتجر" icon="palette" onPress={() => router.push("/vendor/design" as never)} />
            <Action label="المحفظة" icon="account-balance-wallet" onPress={() => router.push("/vendor/wallet" as never)} />
          </View>
          <Text style={styles.sectionTitle}>آخر الطلبات</Text>
        </>}
        ListEmptyComponent={<Text style={styles.empty}>لا توجد طلبات حتى الآن.</Text>}
        renderItem={({ item }) => <View style={styles.order}><View><Text style={styles.orderNumber}>{item.order_number}</Text><Text style={styles.muted}>{item.status}</Text></View><Text style={styles.amount}>{item.total} {item.currency}</Text></View>}
      />
    </ScreenContainer>
  );
}

function Metric({ label, value, icon }: { label: string; value: string; icon: keyof typeof MaterialIcons.glyphMap }) {
  return <View style={styles.metric}><MaterialIcons name={icon} size={23} color="#E60023" /><Text style={styles.metricValue}>{value}</Text><Text style={styles.muted}>{label}</Text></View>;
}

function Action({ label, icon, onPress }: { label: string; icon: keyof typeof MaterialIcons.glyphMap; onPress: () => void }) {
  return <TouchableOpacity style={styles.action} onPress={onPress}><MaterialIcons name={icon} size={25} color="#111" /><Text style={styles.actionText}>{label}</Text></TouchableOpacity>;
}

const styles = StyleSheet.create({
  content: { padding: 14, paddingBottom: 36, direction: "rtl" },
  loading: { flex: 1, justifyContent: "center", alignItems: "center", gap: 10 },
  header: { flexDirection: "row-reverse", alignItems: "center", gap: 12, marginBottom: 14 },
  logo: { width: 48, height: 48, borderRadius: 12, backgroundColor: "#111", alignItems: "center", justifyContent: "center" },
  title: { fontSize: 23, fontWeight: "900", textAlign: "right" },
  muted: { color: "#777", fontSize: 12, textAlign: "right" },
  metrics: { backgroundColor: "#FFF", borderRadius: 10, padding: 15, flexDirection: "row-reverse", justifyContent: "space-around", marginBottom: 12 },
  metric: { alignItems: "center", gap: 4, flex: 1 },
  metricValue: { fontSize: 21, fontWeight: "900" },
  actions: { flexDirection: "row-reverse", gap: 9, marginBottom: 22 },
  action: { flex: 1, backgroundColor: "#FFF", borderRadius: 9, paddingVertical: 14, alignItems: "center", gap: 7 },
  actionText: { fontSize: 11, fontWeight: "700", textAlign: "center" },
  sectionTitle: { fontSize: 18, fontWeight: "900", textAlign: "right", marginBottom: 9 },
  order: { backgroundColor: "#FFF", borderRadius: 8, padding: 14, flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 8 },
  orderNumber: { fontWeight: "800", textAlign: "right" },
  amount: { color: "#E60023", fontWeight: "900" },
  empty: { textAlign: "center", color: "#777", padding: 30 },
});
