import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
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
  useEffect(() => {
    if (selectedTag && tags.length === 0) setSelectedTag(null);
  }, [selectedTag, tags]);

  return (
    <View style={[styles.page, { paddingTop: Math.max(insets.top, 8) }]}>
      <FlatList
        data={trendingProducts}
        keyExtractor={(item) => item.id}
        numColumns={2}
        showsVerticalScrollIndicator={false}
        columnWrapperStyle={trendingProducts.length > 1 ? styles.row : undefined}
        contentContainerStyle={[styles.list, { paddingBottom: 120 + insets.bottom }]}
        refreshing={loading}
        onRefresh={() => load(selectedTag ?? "")}
        renderItem={({ item }) => <ProductCard product={item} />}
        ListHeaderComponent={<View>
          <View style={styles.hero}>
            <Text style={styles.kicker}>TRENDING</Text>
            <Text style={styles.heroTitle}>الترندات</Text>
            <Text style={styles.heroText}>منتجات نشرتها المتاجر ضمن الترندات، مرتبة من خادم المنصة مع تصفية الهاشتاجات.</Text>
          </View>
          <View style={styles.tagSection}>
            <View style={styles.tagTitleRow}><View style={styles.allTags}><MaterialIcons name="local-fire-department" size={19} color="#171717" /></View><View><Text style={styles.tagTitle}>تصفية الترند</Text><Text style={styles.tagSub}>اختر هاشتاجًا أو اعرض الكل</Text></View></View>
            <FlatList horizontal inverted data={availableTags} keyExtractor={(item) => item} showsHorizontalScrollIndicator={false} contentContainerStyle={styles.tags} renderItem={({ item }) => {
              const active = item === "__all__" ? selectedTag === null : selectedTag === item;
              return <TouchableOpacity onPress={() => setSelectedTag(item === "__all__" ? null : item)} style={[styles.tag, active && styles.tagActive]}><Text style={[styles.tagText, active && styles.tagTextActive]}>{item === "__all__" ? "الكل" : `#${item}`}</Text></TouchableOpacity>;
            }} ListEmptyComponent={!loading ? <Text style={styles.noTags}>لا توجد هاشتاجات ترند منشورة الآن.</Text> : null} />
          </View>
          <View style={styles.heading}><Text style={styles.headingText}>{selectedTag ? `#${selectedTag}` : "كل الترندات"}</Text><Text style={styles.count}>{trendingProducts.length} منتج</Text></View>
        </View>}
        ListEmptyComponent={<View style={styles.empty}><MaterialIcons name="local-fire-department" size={44} color="#A0A0A0" /><Text style={styles.emptyTitle}>{loading ? "جارٍ تحميل الترندات" : "لا توجد أصناف مفعلة للترندات"}</Text><Text style={styles.emptyText}>فعّل خيار الترند من بيانات المنتج ليظهر هنا بعد نشره واعتماد المتجر.</Text></View>}
      />
    </View>
  );
}

const styles = StyleSheet.create({ page:{flex:1,backgroundColor:"#FFF"},list:{paddingHorizontal:12},hero:{minHeight:150,backgroundColor:"#171717",padding:18,alignItems:"flex-end",justifyContent:"center",marginHorizontal:-12,borderBottomLeftRadius:18,borderBottomRightRadius:18},kicker:{color:"#E60023",fontWeight:"900",fontSize:10},heroTitle:{color:"#FFF",fontWeight:"900",fontSize:28,marginTop:4},heroText:{color:"#D8D8D8",fontSize:10,marginTop:5,textAlign:"right",lineHeight:17,maxWidth:330},tagSection:{paddingTop:16,paddingBottom:4},tagTitleRow:{flexDirection:"row-reverse",justifyContent:"space-between",alignItems:"center",paddingHorizontal:2,marginBottom:10},tagTitle:{color:"#171717",fontSize:14,fontWeight:"900",textAlign:"right"},tagSub:{color:"#888",fontSize:9,marginTop:2,textAlign:"right"},allTags:{width:36,height:36,borderRadius:10,backgroundColor:"#F1F1F1",alignItems:"center",justifyContent:"center"},tags:{gap:8,paddingBottom:8},tag:{backgroundColor:"#F1F1F1",borderRadius:18,paddingHorizontal:12,paddingVertical:8},tagActive:{backgroundColor:"#171717"},tagText:{color:"#505050",fontSize:11,fontWeight:"800"},tagTextActive:{color:"#FFF"},noTags:{color:"#888",fontSize:11},heading:{flexDirection:"row-reverse",alignItems:"baseline",justifyContent:"space-between",paddingTop:9,paddingBottom:10},headingText:{color:"#171717",fontSize:18,fontWeight:"900"},count:{color:"#888",fontSize:10},row:{gap:10},empty:{alignItems:"center",paddingVertical:50,paddingHorizontal:23},emptyTitle:{color:"#303030",fontSize:15,fontWeight:"900",marginTop:9},emptyText:{color:"#858585",fontSize:11,textAlign:"center",marginTop:5,lineHeight:18}
});
