import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import { ScreenContainer } from "@/components/screen-container";

export default function NotificationsScreen() { return <ScreenContainer edges={["top", "left", "right"]} className="bg-[#F6F6F6]"><View style={styles.header}><TouchableOpacity onPress={() => router.back()}><MaterialIcons name="arrow-forward" size={23} color="#171717" /></TouchableOpacity><Text style={styles.title}>الإشعارات</Text><Text style={styles.readAll}>تعليم الكل كمقروء</Text></View><View style={styles.empty}><MaterialIcons name="notifications-none" size={43} color="#9A9A9A" /><Text style={styles.emptyTitle}>لا توجد إشعارات بعد</Text><Text style={styles.emptyText}>ستظهر عروض الأصناف والطلبات الفعلية هنا.</Text></View></ScreenContainer>; }
const styles = StyleSheet.create({ header: { height: 56, backgroundColor: "#FFFFFF", paddingHorizontal: 15, flexDirection: "row", justifyContent: "space-between", alignItems: "center", borderBottomWidth: 1, borderColor: "#E9E9E9" }, title: { color: "#171717", fontSize: 16, fontWeight: "900" }, readAll: { color: "#777777", fontSize: 10 }, empty: { flex: 1, alignItems: "center", justifyContent: "center", padding: 30 }, emptyTitle: { color: "#252525", fontSize: 16, fontWeight: "900", marginTop: 10 }, emptyText: { color: "#777777", fontSize: 11, marginTop: 5, textAlign: "center" },
});
