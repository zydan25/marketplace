import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ActivityIndicator, FlatList, RefreshControl, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import { useEffect, useState } from "react";
import { ScreenContainer } from "@/components/screen-container";
import { djangoApi } from "@/lib/django-api";

type NotificationItem = { id: number; title: string; body: string; image?: string | null; product?: number | null; is_read: boolean; created_at: string };

export default function NotificationsScreen() {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const load = async () => { try { const data = await djangoApi<{ results?: NotificationItem[] }>("/api/notifications/"); setItems(data.results ?? []); } finally { setLoading(false); setRefreshing(false); } };
  useEffect(() => { load(); }, []);
  const unread = items.some((item) => !item.is_read);
  const markRead = async (id: number) => { try { await djangoApi(`/api/notifications/${id}/mark_read/`, { method: "POST" }); setItems((current) => current.map((item) => item.id === id ? { ...item, is_read: true } : item)); } catch { /* ignore transient read errors */ } };
  return <ScreenContainer edges={["top", "left", "right", "bottom"]} className="bg-[#F6F6F6]"><View style={styles.header}><TouchableOpacity style={styles.headerButton} onPress={() => router.back()}><MaterialIcons name="arrow-forward" size={22} color="#171717" /></TouchableOpacity><Text style={styles.title}>الإشعارات</Text><TouchableOpacity disabled={!unread} onPress={async () => { await Promise.all(items.filter((item) => !item.is_read).map((item) => markRead(item.id))); }}><Text style={[styles.readAll, !unread && styles.disabled]}>تعليم الكل كمقروء</Text></TouchableOpacity></View><FlatList data={items} keyExtractor={(item) => String(item.id)} showsVerticalScrollIndicator={false} contentContainerStyle={styles.list} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} />} renderItem={({ item }) => <TouchableOpacity onPress={() => markRead(item.id)} activeOpacity={0.85} style={[styles.card, !item.is_read && styles.unread]}><View style={[styles.dot, !item.is_read && styles.dotActive]} /><View style={styles.copy}><View style={styles.cardTop}><Text style={styles.date}>{new Date(item.created_at).toLocaleDateString("ar-YE")}</Text><Text style={styles.cardTitle}>{item.title}</Text></View><Text style={styles.body}>{item.body}</Text></View></TouchableOpacity>} ListEmptyComponent={loading ? <View style={styles.empty}><ActivityIndicator color="#E60023" /></View> : <View style={styles.empty}><MaterialIcons name="notifications-none" size={43} color="#9A9A9A" /><Text style={styles.emptyTitle}>لا توجد إشعارات بعد</Text><Text style={styles.emptyText}>ستظهر هنا أخبار الطلبات والعروض المهمة.</Text></View>} /></ScreenContainer>;
}

const styles = StyleSheet.create({
  header: { height: 58, backgroundColor: "#FFF", paddingHorizontal: 12, flexDirection: "row", justifyContent: "space-between", alignItems: "center", borderBottomWidth: 1, borderColor: "#E9E9E9" },
  headerButton: { width: 38, height: 38, borderRadius: 19, backgroundColor: "#F6F6F6", alignItems: "center", justifyContent: "center" },
  title: { color: "#171717", fontSize: 16, fontWeight: "900" },
  readAll: { color: "#E60023", fontSize: 9, fontWeight: "800" }, disabled: { color: "#BBB" },
  list: { padding: 12, paddingBottom: 120 },
  card: { flexDirection: "row-reverse", gap: 10, backgroundColor: "#FFF", borderRadius: 14, padding: 13, marginBottom: 8, borderWidth: 1, borderColor: "#ECECEC" },
  unread: { borderColor: "#FFD5DC", backgroundColor: "#FFF9FA" },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: "transparent", marginTop: 5 }, dotActive: { backgroundColor: "#E60023" },
  copy: { flex: 1 }, cardTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" }, cardTitle: { flex: 1, color: "#222", fontSize: 13, fontWeight: "900", textAlign: "right" }, date: { color: "#999", fontSize: 9, marginLeft: 8 }, body: { color: "#666", fontSize: 10, lineHeight: 17, textAlign: "right", marginTop: 4 },
  empty: { alignItems: "center", justifyContent: "center", minHeight: 360, padding: 30 }, emptyTitle: { color: "#252525", fontSize: 16, fontWeight: "900", marginTop: 10 }, emptyText: { color: "#777", fontSize: 11, marginTop: 5, textAlign: "center" },
});
