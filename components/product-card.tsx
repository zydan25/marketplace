import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { Alert, Image, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";

import type { StoreProduct } from "@/lib/product-api";
import { formatYER } from "@/lib/catalog";
import { useCart } from "@/lib/cart-context";

export function ProductCard({ product }: { product: StoreProduct }) {
  const { addItem } = useCart();
  const discount = product.discountPercent;
  const primaryImage = product.images[0]?.url;

  return (
    <View style={styles.card}>
      <TouchableOpacity activeOpacity={0.82} onPress={() => router.push({ pathname: "/product/[id]", params: { id: product.id } } as never)}>
        <View style={styles.imageWrap}>
          {primaryImage ? <Image source={{ uri: primaryImage }} style={styles.image} resizeMode="cover" /> : <View style={styles.noImage}><MaterialIcons name="image-not-supported" size={28} color="#A3A3A3" /></View>}
          {product.isTrending && product.trendTags[0] ? <View style={styles.trendBadge}><Text style={styles.trendBadgeText}>#{product.trendTags[0]}</Text></View> : null}
          {discount > 0 ? <View style={styles.badge}><Text style={styles.badgeText}>خصم {discount}%</Text></View> : null}
          <TouchableOpacity activeOpacity={0.7} style={styles.wish} onPress={() => Alert.alert("المفضلة", "سيتم ربط قائمة المفضلة بحسابك عند تفعيل الحسابات.")}>
            <MaterialIcons name="favorite-border" size={18} color="#171717" />
          </TouchableOpacity>
        </View>
        <Text style={styles.name} numberOfLines={2}>{product.name}</Text>
        <View style={styles.priceRow}>
          <Text style={styles.price}>{formatYER(product.price)}</Text>
          {discount > 0 ? <Text style={styles.oldPrice}>{formatYER(product.originalPrice)}</Text> : null}
        </View>
        <View style={styles.metaRow}>
          {discount > 0 ? <Text style={styles.discount}>-{discount}%</Text> : <Text style={styles.stock}>سعر ثابت</Text>}
          <Text style={styles.rating}>{product.reviews ? `★ ${product.rating} (${product.reviews})` : "جديد"}</Text>
        </View>
      </TouchableOpacity>
      <TouchableOpacity activeOpacity={0.8} style={styles.addButton} onPress={() => addItem(product, product.colors[0]?.name ?? "افتراضي", product.sizes[0]?.label ?? "مقاس موحد")}>
        <MaterialIcons name="add-shopping-cart" size={19} color="#FFFFFF" />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { flex: 1, minWidth: 0, marginBottom: 16, backgroundColor: "#FFF", borderRadius: 8, overflow: "hidden" },
  imageWrap: { height: 180, backgroundColor: "#F5F5F5", position: "relative" },
  image: { width: "100%", height: "100%" }, 
  noImage: { width: "100%", height: "100%", alignItems: "center", justifyContent: "center" },
  badge: { position: "absolute", right: 0, bottom: 0, backgroundColor: "#E60023", paddingHorizontal: 6, paddingVertical: 4, borderTopLeftRadius: 8 },
  badgeText: { fontSize: 9, color: "#FFFFFF", fontWeight: "800" },
  trendBadge: { position: "absolute", left: 0, top: 0, backgroundColor: "#111", paddingHorizontal: 6, paddingVertical: 4, borderBottomRightRadius: 8 },
  trendBadgeText: { fontSize: 9, color: "#FFFFFF", fontWeight: "800" },
  wish: { position: "absolute", top: 6, right: 6, width: 28, height: 28, backgroundColor: "rgba(255,255,255,0.9)", borderRadius: 14, alignItems: "center", justifyContent: "center" },
  name: { marginTop: 8, paddingHorizontal: 6, color: "#111", fontSize: 12, lineHeight: 18, fontWeight: "500", textAlign: "right" },
  priceRow: { flexDirection: "row-reverse", alignItems: "baseline", gap: 6, marginTop: 4, paddingHorizontal: 6 },
  price: { color: "#111", fontWeight: "900", fontSize: 14 },
  oldPrice: { color: "#999", fontSize: 11, textDecorationLine: "line-through" },
  metaRow: { flexDirection: "row-reverse", justifyContent: "space-between", alignItems: "center", marginTop: 4, paddingHorizontal: 6, paddingBottom: 8 },
  discount: { color: "#E60023", fontSize: 10, fontWeight: "700" }, 
  stock: { color: "#777", fontSize: 10 },
  rating: { color: "#777", fontSize: 10 },
  addButton: { position: "absolute", left: 6, top: 164, width: 32, height: 32, borderRadius: 16, backgroundColor: "#111", alignItems: "center", justifyContent: "center", shadowColor: "#000", shadowOpacity: 0.1, shadowRadius: 4, elevation: 2 },
});
