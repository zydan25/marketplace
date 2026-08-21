import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useCart } from "@/lib/cart-context";

export function ShopHeader({ compact = false, overlay = false, placeholder }: { compact?: boolean; overlay?: boolean; placeholder?: string }) {
  const { itemCount } = useCart(); 
  const insets = useSafeAreaInsets();
  const iconColor = overlay ? "#FFFFFF" : "#161616";
  return <View style={[styles.wrap, { paddingTop: Math.max(insets.top, 8) }, compact && styles.compactWrap, overlay && styles.overlayWrap]}><View style={styles.actions}><TouchableOpacity style={[styles.iconButton, overlay && styles.overlayButton]} onPress={() => router.push("/notifications" as never)}><MaterialIcons name="notifications-none" size={22} color={iconColor} /></TouchableOpacity><TouchableOpacity style={[styles.iconButton, overlay && styles.overlayButton]} onPress={() => router.push("/bag" as never)}><MaterialIcons name="shopping-bag" size={22} color={iconColor} />{itemCount > 0 ? <View style={styles.count}><Text style={styles.countText}>{itemCount}</Text></View> : null}</TouchableOpacity></View>{!compact ? <TouchableOpacity style={[styles.search, overlay && styles.overlaySearch]} onPress={() => router.push("/search" as never)}><MaterialIcons name="search" size={21} color={overlay ? "#383838" : "#575757"} /><TextInput editable={false} pointerEvents="none" style={styles.searchText} placeholder={placeholder || "ابحثي عن فستان، كود، أو ستايل"} placeholderTextColor="#707070" textAlign="right" /><MaterialIcons name="photo-camera" size={20} color={overlay ? "#383838" : "#575757"} /></TouchableOpacity> : null}</View>;
}
const styles = StyleSheet.create({ wrap: { paddingHorizontal: 14, paddingBottom: 8, backgroundColor: "#FFFFFF", flexDirection: "row", alignItems: "center", gap: 8 }, overlayWrap: { position: "absolute", top: 0, left: 0, right: 0, zIndex: 3, backgroundColor: "transparent" }, compactWrap: { justifyContent: "flex-start" }, actions: { flexDirection: "row-reverse", alignItems: "center", gap: 2 }, iconButton: { width: 34, height: 38, alignItems: "center", justifyContent: "center", position: "relative" }, overlayButton: { backgroundColor: "rgba(0,0,0,0.26)", borderRadius: 19 }, count: { position: "absolute", top: 2, right: 1, minWidth: 16, height: 16, borderRadius: 8, backgroundColor: "#E60023", alignItems: "center", justifyContent: "center", paddingHorizontal: 3 }, countText: { color: "#FFFFFF", fontSize: 9, fontWeight: "800" }, search: { flex: 1, height: 40, borderRadius: 3, backgroundColor: "#F3F3F3", paddingHorizontal: 10, flexDirection: "row-reverse", alignItems: "center", gap: 6 }, overlaySearch: { backgroundColor: "rgba(255,255,255,0.94)" }, searchText: { flex: 1, fontSize: 12, color: "#1B1B1B", writingDirection: "rtl" },
});
