import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { Alert, Image, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";

import type { StoreProduct } from "@/lib/product-api";
import { formatYER } from "@/lib/catalog";
import { useCart } from "@/lib/cart-context";

type ProductCardConfig = {
  image_height?: number;
  radius?: number;
  card_style?: string;
  show_wishlist?: boolean;
  show_add_button?: boolean;
  show_rating?: boolean;
  show_stock_label?: boolean;
  show_discount_badge?: boolean;
  show_trend_badge?: boolean;
  name_size?: number;
  price_size?: number;
  gap?: number;
};

export function ProductCard({ product, config = {} }: { product: StoreProduct; config?: ProductCardConfig }) {
  const { addItem } = useCart();
  const discount = product.discountPercent;
  const primaryImage = product.images[0]?.url;
  const imageHeight = Math.max(80, Number(config.image_height ?? 180));
  const radius = Math.max(0, Number(config.radius ?? (config.card_style === "square" ? 0 : 8)));
  const cardStyle = String(config.card_style ?? "rounded");
  const showWishlist = config.show_wishlist !== false;
  const showAdd = config.show_add_button !== false;
  const showRating = config.show_rating !== false;
  const showStock = config.show_stock_label !== false;
  const showDiscountBadge = config.show_discount_badge !== false;
  const showTrendBadge = config.show_trend_badge !== false;

  return (
    <View style={[styles.card, { borderRadius: radius, borderWidth: cardStyle === "outlined" ? 1 : 0, borderColor: "#E8E8E8" }]}>
      <TouchableOpacity activeOpacity={0.82} onPress={() => router.push({ pathname: "/product/[id]", params: { id: product.id } } as never)}>
        <View style={[styles.imageWrap, { height: imageHeight, borderRadius: Math.max(0, radius) }]}>
          {primaryImage ? <Image source={{ uri: primaryImage }} style={styles.image} resizeMode={String((config as any).image_fit ?? "cover") as any} /> : <View style={styles.noImage}><MaterialIcons name="image-not-supported" size={28} color="#A3A3A3" /></View>}
          {showTrendBadge && product.isTrending && product.trendTags[0] ? <View style={styles.trendBadge}><Text style={styles.trendBadgeText}>#{product.trendTags[0]}</Text></View> : null}
          {showDiscountBadge && discount > 0 ? <View style={styles.badge}><Text style={styles.badgeText}>خصم {discount}%</Text></View> : null}
          {showWishlist ? <TouchableOpacity activeOpacity={0.7} style={styles.wish} onPress={() => Alert.alert("المفضلة", "سيتم ربط قائمة المفضلة بحسابك عند تفعيل الحسابات.")}><MaterialIcons name="favorite-border" size={18} color="#171717" /></TouchableOpacity> : null}
        </View>
        <Text style={[styles.name, { fontSize: Number(config.name_size ?? 12) }]} numberOfLines={2}>{product.name}</Text>
        <View style={[styles.priceRow, { marginTop: Number(config.gap ?? 4) }]}>
          <Text style={[styles.price, { fontSize: Number(config.price_size ?? 14) }]}>{formatYER(product.price)}</Text>
          {discount > 0 ? <Text style={styles.oldPrice}>{formatYER(product.originalPrice)}</Text> : null}
        </View>
        <View style={styles.metaRow}>
          {showStock ? <Text style={styles.stock}>{discount > 0 ? `-${discount}%` : "سعر ثابت"}</Text> : <View />}
          {showRating ? <Text style={styles.rating}>{product.reviews ? `★ ${product.rating} (${product.reviews})` : "جديد"}</Text> : null}
        </View>
      </TouchableOpacity>
      {showAdd ? <TouchableOpacity activeOpacity={0.8} style={[styles.addButton, { top: imageHeight - 16 }]} onPress={() => addItem(product, product.colors[0]?.name ?? "افتراضي", product.sizes[0]?.label ?? "مقاس موحد")}><MaterialIcons name="add-shopping-cart" size={19} color="#FFFFFF" /></TouchableOpacity> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { flex: 1, minWidth: 0, marginBottom: 10, backgroundColor: "#FFF", overflow: "hidden" },
  imageWrap: { width: "100%", backgroundColor: "#F5F5F5", position: "relative", overflow: "hidden" },
  image: { width: "100%", height: "100%" },
  noImage: { width: "100%", height: "100%", alignItems: "center", justifyContent: "center" },
  badge: { position: "absolute", right: 0, bottom: 0, backgroundColor: "#E60023", paddingHorizontal: 6, paddingVertical: 4, borderTopLeftRadius: 8 },
  badgeText: { fontSize: 9, color: "#FFFFFF", fontWeight: "800" },
  trendBadge: { position: "absolute", left: 0, top: 0, backgroundColor: "#111", paddingHorizontal: 6, paddingVertical: 4, borderBottomRightRadius: 8 },
  trendBadgeText: { fontSize: 9, color: "#FFFFFF", fontWeight: "800" },
  wish: { position: "absolute", top: 6, right: 6, width: 28, height: 28, backgroundColor: "rgba(255,255,255,0.9)", borderRadius: 14, alignItems: "center", justifyContent: "center" },
  name: { marginTop: 7, paddingHorizontal: 6, color: "#111", lineHeight: 18, fontWeight: "500", textAlign: "right" },
  priceRow: { flexDirection: "row-reverse", alignItems: "baseline", gap: 6, paddingHorizontal: 6 },
  price: { color: "#111", fontWeight: "900" },
  oldPrice: { color: "#999", fontSize: 11, textDecorationLine: "line-through" },
  metaRow: { flexDirection: "row-reverse", justifyContent: "space-between", alignItems: "center", marginTop: 4, paddingHorizontal: 6, paddingBottom: 7 },
  stock: { color: "#777", fontSize: 10 },
  rating: { color: "#777", fontSize: 10 },
  addButton: { position: "absolute", left: 6, width: 32, height: 32, borderRadius: 16, backgroundColor: "#111", alignItems: "center", justifyContent: "center", shadowColor: "#000", shadowOpacity: 0.1, shadowRadius: 4, elevation: 2 },
});
