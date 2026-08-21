import { useEffect, useState, useCallback } from "react";
import { ActivityIndicator, Image, StyleSheet, Text, TouchableOpacity, View, ScrollView, RefreshControl } from "react-native";
import { router } from "expo-router";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ScreenContainer } from "@/components/screen-container";
import { djangoApi, djangoLogout } from "@/lib/django-api";

type Vendor = { store_name: string; status: string; commission_percent: string; logo_url?: string };
type Product = { id: number; name: string; sku: string; effective_price: string; stock: number; is_published: boolean };
type Order = { id: number; order_number: string; status: string; total: string; currency: string; created_at: string };
type Wallet = { balance: string; currency: string };

export default function VendorDashboardScreen() {
  const [vendor, setVendor] = useState<Vendor | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const sessionUser = await djangoApi<{ role?: string }>("/api/auth/me/");
      if (sessionUser.role !== "vendor") {
        router.replace("/login" as never);
        return;
      }
      const [vendorsRes, productsRes, ordersRes, walletsRes] = await Promise.all([
        djangoApi<{ results?: Vendor[] }>("/api/vendors/"),
        djangoApi<{ results?: Product[] }>("/api/products/"),
        djangoApi<{ results?: Order[] }>("/api/orders/"),
        djangoApi<{ results?: Wallet[] }>("/api/wallets/"),
      ]);

      setVendor(vendorsRes.results?.[0] ?? null);
      setProducts(productsRes.results ?? []);
      setOrders(ordersRes.results ?? []);
      setWallet(walletsRes.results?.[0] ?? null);
    } catch (error) {
      console.error("Vendor Load Error:", error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const onRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  async function logout() {
    await djangoLogout();
    router.replace("/vendor/login" as never);
  }

  if (loading) return <ScreenContainer><View style={styles.loading}><ActivityIndicator color="#E60023" /><Text style={styles.muted}>جارٍ تحميل لوحة المتجر...</Text></View></ScreenContainer>;

  return (
    <ScreenContainer className="bg-[#F8F9FA]" edges={["top", "bottom", "left", "right"]}>
      <View style={styles.topBar}>
        <TouchableOpacity onPress={logout} style={styles.iconBtn}><MaterialIcons name="logout" size={22} color="#E60023" /></TouchableOpacity>
        <View style={styles.storeInfo}>
          <Text style={styles.storeName}>{vendor?.store_name || "متجري"}</Text>
          <View style={styles.statusBadge}><View style={[styles.statusDot, { backgroundColor: vendor?.status === "active" ? "#168451" : "#F0B800" }]} /><Text style={styles.statusText}>{vendor?.status === "active" ? "متجر نشط" : "قيد المراجعة"}</Text></View>
        </View>
        <View style={styles.logoBox}>{vendor?.logo_url ? <Image source={{ uri: vendor.logo_url }} style={styles.logo} /> : <MaterialIcons name="storefront" size={26} color="#FFF" />}</View>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}>
        <View style={styles.walletCard}>
          <View style={styles.walletHeader}><MaterialIcons name="account-balance-wallet" size={20} color="#FFF" /><Text style={styles.walletTitle}>رصيد المتجر الحالي</Text></View>
          <Text style={styles.balance}>{wallet?.balance || "0.00"} <Text style={styles.currency}>{wallet?.currency || "ر.ي"}</Text></Text>
          <View style={styles.walletFooter}><Text style={styles.commission}>عمولة المنصة: {vendor?.commission_percent || "0"}%</Text><TouchableOpacity onPress={() => router.push("/vendor/wallet" as never)}><Text style={styles.walletLink}>تفاصيل المحفظة ‹</Text></TouchableOpacity></View>
        </View>

        <View style={styles.grid}>
          <StatCard label="إجمالي المنتجات" value={products.length} icon="inventory-2" color="#3498DB" />
          <StatCard label="طلبات جديدة" value={orders.filter(o => o.status === "pending").length} icon="notification-important" color="#E67E22" />
          <StatCard label="إجمالي الطلبات" value={orders.length} icon="shopping-bag" color="#168451" />
          <StatCard label="المنتجات النشطة" value={products.filter(p => p.is_published).length} icon="check-circle" color="#9B59B6" />
        </View>

        <View style={styles.quickActions}>
          <ActionButton label="إضافة منتج" icon="add-circle-outline" color="#E60023" onPress={() => router.push("/vendor/products" as never)} />
          <ActionButton label="إدارة المنتجات" icon="list-alt" color="#111" onPress={() => router.push("/vendor/products" as never)} />
          <ActionButton label="تصميم المتجر" icon="auto-fix-high" color="#111" onPress={() => router.push("/vendor/design" as never)} />
          <ActionButton label="الطلبات" icon="assignment" color="#111" onPress={() => router.push("/vendor/orders" as never)} />
        </View>

        <View style={styles.sectionHeader}><TouchableOpacity><Text style={styles.seeAll}>عرض الكل</Text></TouchableOpacity><Text style={styles.sectionTitle}>آخر الطلبات الواردة</Text></View>

        {orders.length === 0 ? (
          <View style={styles.emptyState}><MaterialIcons name="history" size={40} color="#CCC" /><Text style={styles.emptyText}>لا توجد طلبات حتى الآن</Text></View>
        ) : (
          orders.slice(0, 5).map(order => (
            <TouchableOpacity key={order.id} style={styles.orderItem}>
              <View style={styles.orderMeta}><Text style={styles.orderNum}>#{order.order_number}</Text><Text style={styles.orderDate}>{new Date(order.created_at).toLocaleDateString("ar-YE")}</Text></View>
              <View style={styles.orderStatus}><Text style={styles.orderAmount}>{order.total} {order.currency}</Text><View style={[styles.badge, { backgroundColor: getStatusColor(order.status) + "20" }]}><Text style={[styles.badgeText, { color: getStatusColor(order.status) }]}>{translateStatus(order.status)}</Text></View></View>
            </TouchableOpacity>
          ))
        )}
      </ScrollView>
    </ScreenContainer>
  );
}

function StatCard({ label, value, icon, color }: { label: string; value: number | string; icon: any; color: string }) {
  return <View style={styles.statCard}><View style={[styles.statIcon, { backgroundColor: color + "15" }]}><MaterialIcons name={icon} size={20} color={color} /></View><Text style={styles.statValue}>{value}</Text><Text style={styles.statLabel}>{label}</Text></View>;
}

function ActionButton({ label, icon, color, onPress }: { label: string; icon: any; color: string; onPress: () => void }) {
  return <TouchableOpacity style={styles.actionBtn} onPress={onPress}><View style={[styles.actionIcon, { backgroundColor: color }]}><MaterialIcons name={icon} size={22} color="#FFF" /></View><Text style={styles.actionLabel}>{label}</Text></TouchableOpacity>;
}

function getStatusColor(status: string) {
  switch (status) {
    case "pending": return "#E67E22";
    case "processing": return "#3498DB";
    case "shipped": return "#9B59B6";
    case "delivered": return "#168451";
    case "cancelled": return "#E60023";
    default: return "#777";
  }
}

function translateStatus(status: string) {
  const map: Record<string, string> = { pending: "قيد الانتظار", processing: "قيد التجهيز", shipped: "تم الشحن", delivered: "تم التسليم", cancelled: "ملغى" };
  return map[status] || status;
}

const styles = StyleSheet.create({
  loading: { flex: 1, justifyContent: "center", alignItems: "center", gap: 12 },
  muted: { color: "#777", fontSize: 13 },
  topBar: { height: 70, backgroundColor: "#FFF", flexDirection: "row", alignItems: "center", paddingHorizontal: 16, borderBottomWidth: 1, borderColor: "#EEE" },
  iconBtn: { width: 40, height: 40, alignItems: "center", justifyContent: "center" },
  storeInfo: { flex: 1, alignItems: "flex-end", paddingRight: 12 },
  storeName: { fontSize: 18, fontWeight: "900", color: "#111" },
  statusBadge: { flexDirection: "row-reverse", alignItems: "center", marginTop: 2 },
  statusDot: { width: 6, height: 6, borderRadius: 3, marginLeft: 5 },
  statusText: { fontSize: 11, color: "#777", fontWeight: "600" },
  logoBox: { width: 44, height: 44, borderRadius: 10, backgroundColor: "#111", alignItems: "center", justifyContent: "center", overflow: "hidden" },
  logo: { width: "100%", height: "100%" },
  scrollContent: { padding: 16, paddingBottom: 40 },
  walletCard: { backgroundColor: "#111", borderRadius: 16, padding: 20, marginBottom: 20 },
  walletHeader: { flexDirection: "row-reverse", alignItems: "center", gap: 8, opacity: 0.8 },
  walletTitle: { color: "#FFF", fontSize: 13, fontWeight: "700" },
  balance: { color: "#FFF", fontSize: 32, fontWeight: "900", textAlign: "right", marginTop: 10 },
  currency: { fontSize: 16, fontWeight: "600", opacity: 0.7 },
  walletFooter: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginTop: 15, borderTopWidth: 1, borderTopColor: "rgba(255,255,255,0.1)", paddingTop: 12 },
  commission: { color: "#FFF", fontSize: 11, opacity: 0.6 },
  walletLink: { color: "#FFF", fontSize: 12, fontWeight: "800" },
  grid: { flexDirection: "row-reverse", flexWrap: "wrap", gap: 10, marginBottom: 20 },
  statCard: { width: "48.5%", backgroundColor: "#FFF", borderRadius: 12, padding: 15, alignItems: "flex-end", borderWidth: 1, borderColor: "#F0F0F0" },
  statIcon: { width: 36, height: 36, borderRadius: 18, alignItems: "center", justifyContent: "center", marginBottom: 10 },
  statValue: { fontSize: 20, fontWeight: "900", color: "#111" },
  statLabel: { fontSize: 11, color: "#777", marginTop: 2 },
  quickActions: { flexDirection: "row-reverse", gap: 10, marginBottom: 25 },
  actionBtn: { flex: 1, alignItems: "center", gap: 8 },
  actionIcon: { width: 50, height: 50, borderRadius: 15, alignItems: "center", justifyContent: "center", shadowColor: "#000", shadowOpacity: 0.05, shadowRadius: 5, elevation: 2 },
  actionLabel: { fontSize: 10, fontWeight: "800", color: "#444", textAlign: "center" },
  sectionHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 12 },
  sectionTitle: { fontSize: 17, fontWeight: "900", color: "#111" },
  seeAll: { color: "#E60023", fontSize: 12, fontWeight: "700" },
  orderItem: { backgroundColor: "#FFF", borderRadius: 12, padding: 15, marginBottom: 10, flexDirection: "row-reverse", justifyContent: "space-between", alignItems: "center", borderWidth: 1, borderColor: "#F0F0F0" },
  orderMeta: { alignItems: "flex-end" },
  orderNum: { fontSize: 14, fontWeight: "800", color: "#111" },
  orderDate: { fontSize: 11, color: "#999", marginTop: 4 },
  orderStatus: { alignItems: "flex-start" },
  orderAmount: { fontSize: 15, fontWeight: "900", color: "#111", marginBottom: 5 },
  badge: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6 },
  badgeText: { fontSize: 10, fontWeight: "800" },
  emptyState: { padding: 40, alignItems: "center", backgroundColor: "#FFF", borderRadius: 12, borderStyle: "dashed", borderWidth: 1, borderColor: "#DDD" },
  emptyText: { color: "#999", fontSize: 13, marginTop: 10 },
});
