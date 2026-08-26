import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ActivityIndicator, FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import { useEffect, useState } from "react";

import { AdminLayout, AdminBadge, AdminEmptyState, getStatusVariant, Colors, Font, Radius, Shadow, Spacing } from "@/components/admin";
import { useAuth } from "@/hooks/use-auth";
import { formatYER } from "@/lib/catalog";
import { getAdminOrders, type StoreOrder } from "@/lib/order-api";

export default function AdminOrdersScreen() {
  const { user, isAuthenticated } = useAuth();
  const [orders, setOrders] = useState<StoreOrder[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      setLoading(true);
      setOrders(await getAdminOrders());
    } finally { setLoading(false); }
  };

  useEffect(() => { if (isAuthenticated && user?.role === "admin") load(); }, [isAuthenticated, user?.role]);

  return (
    <AdminLayout title="الطلبات والدردشات">
      {loading ? (
        <ActivityIndicator color={Colors.primary} style={{ marginTop: 40 }} />
      ) : (
        <FlatList
          style={{ flex: 1 }}
          data={orders}
          keyExtractor={(item) => String(item.id)}
          contentContainerStyle={styles.list}
          refreshing={loading}
          onRefresh={load}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={styles.card}
              activeOpacity={0.7}
              onPress={() => router.push(`/order/${item.id}` as never)}
            >
              <View style={styles.cardLeft}>
                <MaterialIcons name="chat-bubble-outline" size={20} color={Colors.textMuted} />
              </View>
              <View style={styles.cardCopy}>
                <View style={styles.cardHeader}>
                  <Text style={styles.cardName}>{item.customer?.name ?? "عميل"}</Text>
                  <Text style={styles.cardCode}>{item.orderCode}</Text>
                </View>
                <Text style={styles.cardMeta}>
                  {item.customer?.phone} · {item.items.length} أصناف · {formatYER(item.totalAmount)}
                </Text>
                <View style={styles.badgeRow}>
                  <AdminBadge label={item.statusLabel} variant={getStatusVariant(item.status)} />
                </View>
              </View>
              <MaterialIcons name="chevron-left" size={20} color={Colors.textMuted} />
            </TouchableOpacity>
          )}
          ListEmptyComponent={
            <AdminEmptyState
              icon="receipt-long"
              title="لا توجد طلبات"
              description="ستظهر الطلبات الجديدة هنا فور وصولها."
            />
          }
        />
      )}
    </AdminLayout>
  );
}

const styles = StyleSheet.create({
  list: { padding: Spacing.lg, paddingBottom: Spacing["4xl"] },
  card: {
    flexDirection: "row-reverse",
    alignItems: "center",
    backgroundColor: Colors.surface,
    borderRadius: Radius.md,
    padding: Spacing.md,
    marginBottom: Spacing.sm,
    gap: Spacing.md,
    ...Shadow.soft,
  },
  cardLeft: {
    width: 40,
    height: 40,
    borderRadius: Radius.sm,
    backgroundColor: Colors.surfaceAlt,
    alignItems: "center",
    justifyContent: "center",
  },
  cardCopy: { flex: 1, alignItems: "flex-end" },
  cardHeader: { flexDirection: "row-reverse", alignItems: "center", gap: Spacing.sm },
  cardName: { color: Colors.text, ...Font.cardTitle },
  cardCode: { color: Colors.textMuted, ...Font.tiny },
  cardMeta: { color: Colors.textSecondary, ...Font.tiny, marginTop: Spacing.xs, textAlign: "right" },
  badgeRow: { marginTop: Spacing.xs },
});
