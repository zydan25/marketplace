import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { FlatList, RefreshControl, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useEffect, useMemo, useState } from "react";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { ProductCard } from "@/components/product-card";
import { getTrendingProducts, type StoreProduct } from "@/lib/product-api";

export default function TrendsScreen() {
  const [products, setProducts] = useState<StoreProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const insets = useSafeAreaInsets();

  async function load(tag = "") {
    try { setLoading(true); setProducts(await getTrendingProducts(tag)); }
    catch { setProducts([]); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(selectedTag ?? ""); }, [selectedTag]);

  const tags = useMemo(() => [...new Set(products.flatMap((product) => product.trendTags))].filter(Boolean), [products]);
  const trendingProducts = useMemo(() => selectedTag ? products.filter((product) => product.isTrending && product.trendTags.includes(selectedTag)) : products.filter((product) => product.isTrending), [products, selectedTag]);
  const availableTags = useMemo(() => ["__all__", ...tags], [tags]);

  return <View style={[styles.page, { paddingTop: Math.max(insets.top, 8) }]}>
    <FlatList
      data={trendingProducts}
      keyExtractor={(item) => String(item.id)}
      numColumns={2}
      showsVerticalScrollIndicator={false}
      columnWrapperStyle={trendingProducts.length > 1 ? styles.row : undefined}
      contentContainerStyle={[styles.list, { paddingBottom: 120 + insets.bottom }]}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={() => load(selectedTag ?? "")} />}
      renderItem={({ item }) => <ProductCard product={item} />}
      ListHeaderComponent={<View>
        <View style={styles.hero}><View style={styles.fire}><MaterialIcons name="local-fire-department" size={21} color="#FFF"/></View><View style={styles.heroCopy}><Text style={styles.heroTitle}>الترندات</Text><Text style={styles.heroText}>اكتشف المنتجات الأكثر رواجًا الآن، مع تصفية مباشرة حسب الهاشتاج.</Text></View></View>
        <View style={styles.tagSection}><View style={styles.tagHeader}><View><Text style={styles.tagTitle}>تصفح الترند حسب الاهتمام</Text><Text style={styles.tagSub}>اختر هاشتاجًا أو اعرض جميع المنتجات</Text></View><View style={styles.tagIcon}><MaterialIcons name="local-fire-department" size={18} color="#E11D48"/></View></View><FlatList horizontal inverted data={availableTags} keyExtractor={(item) => item} showsHorizontalScrollIndicator={false} contentContainerStyle={styles.tags} renderItem={({ item }) => { const active = item === "__all__" ? selectedTag === null : selectedTag === item; return <TouchableOpacity onPress={() => setSelectedTag(item === "__all__" ? null : item)} style={[styles.tag, active && styles.tagActive]}><Text style={[styles.tagText, active && styles.tagTextActive]}>{item === "__all__" ? "الكل" : `#${item}`}</Text></TouchableOpacity>; }} /></View>
        <View style={styles.heading}><Text style={styles.headingText}>{selectedTag ? `#${selectedTag}` : "الأكثر رواجًا"}</Text><Text style={styles.count}>{trendingProducts.length} منتج</Text></View>
      </View>}
      ListEmptyComponent={<View style={styles.empty}><MaterialIcons name="local-fire-department" size={46} color="#C1C1C5"/><Text style={styles.emptyTitle}>{loading ? "جارٍ تحميل الترندات" : "لا توجد منتجات ترند الآن"}</Text><Text style={styles.emptyText}>تظهر المنتجات هنا بعد نشرها واعتماد المتجر وتفعيل خيار الترند من بيانات المنتج.</Text></View>}
    />
  </View>;
}

const styles = StyleSheet.create({page:{flex:1,backgroundColor:"#F7F7F8"},list:{paddingHorizontal:12},row:{gap:10},hero:{marginHorizontal:-12,backgroundColor:"#111",padding:18,borderBottomLeftRadius:22,borderBottomRightRadius:22,flexDirection:"row-reverse",alignItems:"center",gap:11},fire:{width:44,height:44,borderRadius:14,backgroundColor:"#E11D48",alignItems:"center",justifyContent:"center"},heroCopy:{flex:1,alignItems:"flex-end"},heroTitle:{color:"#FFF",fontSize:27,fontWeight:"900"},heroText:{color:"#CFCFD1",fontSize:10,lineHeight:17,textAlign:"right",marginTop:4},tagSection:{backgroundColor:"#FFF",borderRadius:17,marginTop:12,padding:13,borderWidth:1,borderColor:"#E7E7EA"},tagHeader:{flexDirection:"row-reverse",justifyContent:"space-between",alignItems:"center"},tagIcon:{width:35,height:35,borderRadius:11,backgroundColor:"#FFF0F3",alignItems:"center",justifyContent:"center"},tagTitle:{fontSize:13,fontWeight:"900",color:"#222",textAlign:"right"},tagSub:{fontSize:9,color:"#888",marginTop:2,textAlign:"right"},tags:{gap:7,paddingTop:11,paddingBottom:2},tag:{backgroundColor:"#F0F0F2",paddingHorizontal:12,paddingVertical:8,borderRadius:18},tagActive:{backgroundColor:"#111"},tagText:{fontSize:10,fontWeight:"800",color:"#555"},tagTextActive:{color:"#FFF"},heading:{flexDirection:"row-reverse",justifyContent:"space-between",alignItems:"baseline",paddingTop:14,paddingBottom:10},headingText:{fontSize:17,fontWeight:"900",color:"#222"},count:{fontSize:10,color:"#888"},empty:{backgroundColor:"#FFF",borderRadius:17,alignItems:"center",paddingHorizontal:26,paddingVertical:55,borderWidth:1,borderColor:"#E7E7EA"},emptyTitle:{fontSize:15,fontWeight:"900",color:"#333",marginTop:9},emptyText:{fontSize:10,color:"#888",lineHeight:18,textAlign:"center",marginTop:4}
});
