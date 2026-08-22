import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { Alert, FlatList, Image, Platform, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useEffect, useMemo, useState } from "react";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { formatYER } from "@/lib/catalog";
import { useCart } from "@/lib/cart-context";
import { router } from "expo-router";

export default function BagScreen() {
  const { items, itemCount, updateQuantity, removeItem } = useCart();
  const insets = useSafeAreaInsets();
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  useEffect(() => {
    setSelectedIds((current) => {
      const existing = current.filter((id) => items.some((item) => item.lineId === id));
      return current.length ? existing : items.map((item) => item.lineId);
    });
  }, [items]);
  const selectedItems = useMemo(() => items.filter((item) => selectedIds.includes(item.lineId)), [items, selectedIds]);
  const selectedQuantity = selectedItems.reduce((total, item) => total + item.quantity, 0);
  const subtotal = selectedItems.reduce((total, item) => total + item.product.price * item.quantity, 0);
  const saved = selectedItems.reduce((total, item) => total + Math.max(0, item.product.originalPrice - item.product.price) * item.quantity, 0);
  const allSelected = items.length > 0 && selectedIds.length === items.length;
  const toggleItem = (id: string) => setSelectedIds((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  const toggleAll = () => setSelectedIds(allSelected ? [] : items.map((item) => item.lineId));
  const checkout = () => {
    if (!selectedItems.length) { Alert.alert("اختر منتجًا", "اختر منتجًا واحدًا على الأقل لإكمال الدفع."); return; }
    router.push({ pathname: "/checkout", params: { lines: selectedIds.join(",") } } as never);
  };
  if (!items.length) return <EmptyBag />;
  return (
    <View style={styles.page}>
      <FlatList
        data={items}
        keyExtractor={(item) => item.lineId}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={[styles.list, { paddingBottom: 190 + insets.bottom }]}
        renderItem={({ item }) => <View style={styles.itemCard}>
          <TouchableOpacity style={styles.checkbox} onPress={() => toggleItem(item.lineId)} accessibilityLabel={selectedIds.includes(item.lineId) ? "إلغاء تحديد المنتج" : "تحديد المنتج"}>
            <MaterialIcons name={selectedIds.includes(item.lineId) ? "check-box" : "check-box-outline-blank"} size={23} color={selectedIds.includes(item.lineId) ? "#171717" : "#A4A4A4"} />
          </TouchableOpacity>
          {item.product.images[0]?.url ? <Image source={{ uri: item.product.images[0].url }} style={styles.itemImage} /> : <View style={[styles.itemImage, styles.missingImage]}><MaterialIcons name="image-not-supported" size={23} color="#999" /></View>}
          <View style={styles.itemInfo}>
            <View style={styles.itemTop}><TouchableOpacity onPress={() => removeItem(item.lineId)} style={styles.delete}><MaterialIcons name="delete-outline" size={19} color="#5E5E5E" /></TouchableOpacity><Text style={styles.itemName} numberOfLines={2}>{item.product.name}</Text></View>
            <Text style={styles.variant}>اللون: {item.color} · المقاس: {item.size}</Text>
            <View style={styles.priceLine}><View style={styles.stepper}><TouchableOpacity style={styles.stepButton} onPress={() => updateQuantity(item.lineId, item.quantity - 1)}><MaterialIcons name="remove" size={17} color="#171717" /></TouchableOpacity><Text style={styles.quantity}>{item.quantity}</Text><TouchableOpacity style={styles.stepButton} onPress={() => updateQuantity(item.lineId, item.quantity + 1)}><MaterialIcons name="add" size={17} color="#171717" /></TouchableOpacity></View><View style={styles.priceCopy}><Text style={styles.itemPrice}>{formatYER(item.product.price * item.quantity)}</Text>{item.product.discountPercent > 0 ? <Text style={styles.oldPrice}>{formatYER(item.product.originalPrice * item.quantity)}</Text> : null}</View></View>
          </View>
        </View>}
        ListHeaderComponent={<View><View style={styles.header}><View><Text style={styles.title}>حقيبة التسوق</Text><Text style={styles.countText}>{itemCount} منتج</Text></View><MaterialIcons name="shopping-bag" size={23} color="#111" /></View><View style={styles.delivery}><MaterialIcons name="local-shipping" size={18} color="#168451" /><Text style={styles.deliveryText}>راجع اختياراتك ثم أكمل عملية الدفع بأمان.</Text></View></View>}
        ListFooterComponent={<View style={styles.footerHint}><MaterialIcons name="lock-outline" size={16} color="#777" /><Text style={styles.footerHintText}>الإجمالي الظاهر هنا تقديري؛ يتم اعتماد السعر النهائي من الخادم عند الدفع.</Text></View>}
      />
      <View style={[styles.bottomBar, { bottom: Platform.OS === "web" ? 78 : Math.max(insets.bottom, 8) + 60 }]}>
        <TouchableOpacity style={styles.selectAll} onPress={toggleAll}><MaterialIcons name={allSelected ? "check-box" : "check-box-outline-blank"} size={22} color="#171717" /><Text style={styles.selectAllText}>الكل</Text></TouchableOpacity>
        <View style={styles.totalBox}><Text style={styles.saved}>{saved ? `وفّرت ${formatYER(saved)}` : "إجمالي المنتجات المحددة"}</Text><Text style={styles.total}>{formatYER(subtotal)}</Text></View>
        <TouchableOpacity style={[styles.checkout, !selectedItems.length && styles.checkoutDisabled]} onPress={checkout}><Text style={styles.checkoutText}>إكمال الدفع ({selectedQuantity})</Text></TouchableOpacity>
      </View>
    </View>
  );
}
function EmptyBag() { return <View style={styles.empty}><View style={styles.emptyIcon}><MaterialIcons name="shopping-bag" size={42} color="#1B1B1B" /></View><Text style={styles.emptyTitle}>حقيبتك فارغة</Text><Text style={styles.emptySub}>اكتشف المنتجات الجديدة وأضف ما يعجبك.</Text><TouchableOpacity style={styles.startButton} onPress={() => router.replace("/")}><Text style={styles.startButtonText}>ابدأ التسوق</Text></TouchableOpacity></View>; }
const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: "#F9F9F9" },
  list: { paddingHorizontal: 12, paddingTop: 10 },
  header: { backgroundColor: "#FFF", padding: 14, borderRadius: 12, marginBottom: 8, flexDirection: "row-reverse", justifyContent: "space-between", alignItems: "center" },
  title: { color: "#111", fontSize: 18, fontWeight: "900", textAlign: "right" },
  countText: { color: "#777", fontSize: 10, marginTop: 3, textAlign: "right" },
  delivery: { flexDirection: "row-reverse", gap: 8, alignItems: "center", backgroundColor: "#F0FDF4", padding: 12, borderRadius: 10, marginBottom: 2 },
  deliveryText: { color: "#166534", fontSize: 11, flex: 1, textAlign: "right" },
  itemCard: { minHeight: 120, marginTop: 10, padding: 10, backgroundColor: "#FFF", borderRadius: 14, flexDirection: "row-reverse", gap: 10, borderWidth: 1, borderColor: "#EEE" },
  checkbox: { justifyContent: "center", width: 24 },
  itemImage: { width: 70, height: 92, backgroundColor: "#F5F5F5", borderRadius: 9 },
  missingImage: { alignItems: "center", justifyContent: "center" },
  itemInfo: { flex: 1, minWidth: 0, alignItems: "flex-end" },
  itemTop: { flexDirection: "row", justifyContent: "space-between", width: "100%", gap: 8 },
  delete: { padding: 4 },
  itemName: { flex: 1, textAlign: "right", color: "#111", fontSize: 12, lineHeight: 17, fontWeight: "700" },
  variant: { color: "#777", fontSize: 10, marginTop: 4, textAlign: "right" },
  priceLine: { marginTop: 10, width: "100%", flexDirection: "row", alignItems: "flex-end", justifyContent: "space-between" },
  priceCopy: { alignItems: "flex-end" }, itemPrice: { color: "#111", fontWeight: "900", fontSize: 14 }, oldPrice: { color: "#999", fontSize: 10, marginTop: 2, textDecorationLine: "line-through" },
  stepper: { height: 32, borderRadius: 16, backgroundColor: "#F5F5F5", flexDirection: "row", alignItems: "center", paddingHorizontal: 4 }, stepButton: { width: 28, alignItems: "center", justifyContent: "center" }, quantity: { width: 24, textAlign: "center", color: "#111", fontSize: 13, fontWeight: "800" },
  footerHint: { flexDirection: "row-reverse", gap: 6, alignItems: "center", padding: 16, justifyContent: "center" }, footerHintText: { color: "#777", fontSize: 10, textAlign: "center" },
  bottomBar: { position: "absolute", left: 0, right: 0, zIndex: 20, elevation: 20, backgroundColor: "#FFF", borderTopWidth: 1, borderColor: "#EAEAEA", paddingHorizontal: 12, paddingVertical: 10, flexDirection: "row-reverse", alignItems: "center", gap: 9 },
  selectAll: { alignItems: "center", gap: 2, width: 32 }, selectAllText: { color: "#555", fontSize: 9 }, totalBox: { flex: 1, minWidth: 0, alignItems: "flex-end" }, saved: { color: "#168451", fontSize: 9, minHeight: 13 }, total: { color: "#111", fontWeight: "900", fontSize: 15, marginTop: 2 }, checkout: { backgroundColor: "#111", minWidth: 126, height: 42, borderRadius: 21, alignItems: "center", justifyContent: "center", paddingHorizontal: 13 }, checkoutDisabled: { backgroundColor: "#DADADA" }, checkoutText: { color: "#FFF", fontWeight: "800", fontSize: 12 },
  empty: { flex: 1, backgroundColor: "#FFF", alignItems: "center", justifyContent: "center", padding: 32 }, emptyIcon: { width: 72, height: 72, borderRadius: 36, backgroundColor: "#F5F5F5", alignItems: "center", justifyContent: "center" }, emptyTitle: { color: "#111", fontSize: 18, fontWeight: "900", marginTop: 16 }, emptySub: { color: "#777", fontSize: 13, marginTop: 8, textAlign: "center" }, startButton: { marginTop: 24, backgroundColor: "#111", borderRadius: 22, paddingHorizontal: 24, paddingVertical: 12 }, startButtonText: { color: "#FFF", fontSize: 14, fontWeight: "800" },
});
