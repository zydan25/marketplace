import { useEffect, useState } from "react";
import { FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ScreenContainer } from "@/components/screen-container";
import { ApiClient } from "@/lib/api-client";
import { formatYER } from "@/lib/catalog";

type ReportData = {
  wallet_balance: string;
  total_spent: string;
  orders_count: number;
  recent_transactions: any[];
};

export default function CustomerReportsScreen() {
  const [data, setData] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // In a real app, this would be a dedicated endpoint like /api/reports/customer/
    // For now we'll fetch wallet and orders separately and combine
    Promise.all([
      ApiClient.get<any>("/api/wallets/"),
      ApiClient.get<any>("/api/orders/")
    ]).then(([walletRes, ordersRes]) => {
      const wallet = walletRes.results?.[0];
      const orders = ordersRes.results || [];
      const spent = orders.reduce((sum: number, o: any) => sum + parseFloat(o.total || 0), 0);
      
      setData({
        wallet_balance: wallet?.balance || "0.00",
        total_spent: spent.toFixed(2),
        orders_count: orders.length,
        recent_transactions: wallet?.transactions || []
      });
    }).catch(console.error).finally(() => setLoading(false));
  }, []);

  return (
    <ScreenContainer edges={["top", "bottom", "left", "right"]} className="bg-[#F5F5F5]">
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}><MaterialIcons name="arrow-forward" size={25} /></TouchableOpacity>
        <Text style={styles.title}>تقارير الحساب</Text>
        <View style={{ width: 25 }} />
      </View>
      
      {loading ? (
        <View style={styles.center}><Text>جارٍ التحميل...</Text></View>
      ) : (
        <FlatList
          data={data?.recent_transactions}
          keyExtractor={(item) => String(item.id)}
          contentContainerStyle={styles.content}
          ListHeaderComponent={
            <>
              <View style={styles.summaryRow}>
                <View style={styles.summaryCard}>
                  <Text style={styles.summaryLabel}>الرصيد الحالي</Text>
                  <Text style={styles.summaryValue}>{formatYER(Number(data?.wallet_balance))}</Text>
                </View>
                <View style={styles.summaryCard}>
                  <Text style={styles.summaryLabel}>إجمالي المشتريات</Text>
                  <Text style={[styles.summaryValue, {color: "#E60023"}]}>{formatYER(Number(data?.total_spent))}</Text>
                </View>
              </View>
              <View style={styles.singleCard}>
                <Text style={styles.summaryLabel}>عدد الطلبات المكتملة</Text>
                <Text style={styles.summaryValue}>{data?.orders_count} طلب</Text>
              </View>
              <Text style={styles.sectionTitle}>كشف الحساب (آخر العمليات)</Text>
            </>
          }
          ListEmptyComponent={<Text style={styles.empty}>لا توجد عمليات مسجلة.</Text>}
          renderItem={({ item }) => (
            <View style={styles.transaction}>
              <View>
                <Text style={styles.transNote}>{item.note || item.transaction_type}</Text>
                <Text style={styles.transDate}>{new Date(item.created_at).toLocaleDateString("ar-SA")}</Text>
              </View>
              <View style={{ alignItems: "flex-start" }}>
                <Text style={[styles.transAmount, { color: parseFloat(item.amount) > 0 ? "#168451" : "#E60023" }]}>
                  {parseFloat(item.amount) > 0 ? "+" : ""}{item.amount}
                </Text>
                <Text style={styles.transBalance}>الرصيد: {item.balance_after}</Text>
              </View>
            </View>
          )}
        />
      )}
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  header: { padding: 16, backgroundColor: "#FFF", flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  title: { fontSize: 20, fontWeight: "900" },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  content: { padding: 14 },
  summaryRow: { flexDirection: "row-reverse", gap: 10, marginBottom: 10 },
  summaryCard: { flex: 1, backgroundColor: "#FFF", padding: 16, borderRadius: 10, alignItems: "center" },
  singleCard: { backgroundColor: "#FFF", padding: 16, borderRadius: 10, alignItems: "center", marginBottom: 20 },
  summaryLabel: { color: "#777", fontSize: 13, marginBottom: 6 },
  summaryValue: { fontSize: 18, fontWeight: "900", color: "#111" },
  sectionTitle: { fontSize: 17, fontWeight: "900", textAlign: "right", marginBottom: 12 },
  transaction: { backgroundColor: "#FFF", padding: 14, borderRadius: 8, flexDirection: "row-reverse", justifyContent: "space-between", alignItems: "center", marginBottom: 8 },
  transNote: { fontSize: 14, fontWeight: "700", textAlign: "right" },
  transDate: { color: "#888", fontSize: 11, textAlign: "right", marginTop: 4 },
  transAmount: { fontSize: 15, fontWeight: "900" },
  transBalance: { color: "#666", fontSize: 11, marginTop: 4 },
  empty: { textAlign: "center", color: "#777", marginTop: 20 }
});
