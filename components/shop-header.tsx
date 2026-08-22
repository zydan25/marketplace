import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useCart } from "@/lib/cart-context";

export function ShopHeader({ compact = false, overlay = false, placeholder }: { compact?: boolean; overlay?: boolean; placeholder?: string }) {
  const { itemCount } = useCart();
  const insets = useSafeAreaInsets();
  const iconColor = overlay ? "#FFF" : "#161616";
  return (
    <View style={[styles.wrap, { paddingTop: Math.max(insets.top, 8) }, compact && styles.compactWrap, overlay && styles.overlayWrap]}>
      <View style={styles.actions}>
        <TouchableOpacity style={[styles.iconButton, overlay && styles.overlayButton]} onPress={() => router.push("/notifications" as never)} accessibilityLabel="الإشعارات">
          <MaterialIcons name="notifications-none" size={21} color={iconColor} />
        </TouchableOpacity>
        <TouchableOpacity style={[styles.iconButton, overlay && styles.overlayButton]} onPress={() => router.push("/bag" as never)} accessibilityLabel="السلة">
          <MaterialIcons name="shopping-bag" size={21} color={iconColor} />
          {itemCount > 0 ? <View style={styles.count}><Text style={styles.countText}>{itemCount > 99 ? "99+" : itemCount}</Text></View> : null}
        </TouchableOpacity>
      </View>
      {!compact ? (
        <TouchableOpacity style={[styles.search, overlay && styles.overlaySearch]} onPress={() => router.push("/search" as never)} activeOpacity={0.85}>
          <MaterialIcons name="photo-camera" size={19} color={overlay ? "#383838" : "#575757"} />
          <Text numberOfLines={1} style={styles.searchText}>{placeholder || "ابحث عن منتج أو متجر"}</Text>
          <MaterialIcons name="search" size={20} color={overlay ? "#383838" : "#575757"} />
        </TouchableOpacity>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { paddingHorizontal: 12, paddingBottom: 8, backgroundColor: "#FFF", flexDirection: "row", alignItems: "center", gap: 8 },
  overlayWrap: { position: "absolute", top: 0, left: 0, right: 0, zIndex: 3, backgroundColor: "transparent" },
  compactWrap: { justifyContent: "flex-start" },
  actions: { flexDirection: "row-reverse", alignItems: "center", gap: 2 },
  iconButton: { width: 38, height: 40, borderRadius: 20, alignItems: "center", justifyContent: "center", position: "relative" },
  overlayButton: { backgroundColor: "rgba(0,0,0,0.26)" },
  count: { position: "absolute", top: 1, right: 1, minWidth: 16, height: 16, borderRadius: 8, backgroundColor: "#E60023", alignItems: "center", justifyContent: "center", paddingHorizontal: 3 },
  countText: { color: "#FFF", fontSize: 8, fontWeight: "900" },
  search: { flex: 1, minWidth: 0, height: 40, borderRadius: 8, backgroundColor: "#F3F3F3", paddingHorizontal: 10, flexDirection: "row-reverse", alignItems: "center", gap: 6 },
  overlaySearch: { backgroundColor: "rgba(255,255,255,0.94)" },
  searchText: { flex: 1, minWidth: 0, fontSize: 12, color: "#1B1B1B", textAlign: "right", writingDirection: "rtl" },
});
