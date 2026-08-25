import { useEffect, useState } from "react";
import { ActivityIndicator, FlatList, Image, Pressable, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ScreenContainer } from "@/components/screen-container";
import { ApiClient } from "@/lib/api-client";
import { getProducts, type StoreProduct } from "@/lib/product-api";
import { getVendorStorefront, type StorefrontTab } from "@/lib/storefront-api";
import { ProductCard } from "@/components/product-card";
import { ShareButton } from "@/components/share-button";

type Store = { store_name: string; slug: string; description?: string; logo_url?: string | null; cover_url?: string | null };

export default function StoreScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const [store, setStore] = useState<Store | null>(null);
  const [products, setProducts] = useState<StoreProduct[]>([]);
  const [sections, setSections] = useState<StorefrontTab[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      ApiClient.get<Store>(`/api/vendors/${slug}/`),
      getProducts(),
      getVendorStorefront(String(slug)),
    ]).then(([data, items, storefront]) => {
      setStore(data);
      setProducts(items.filter(item => item.vendor.slug === slug));
      setSections(storefront);
    }).catch(() => undefined).finally(() => setLoading(false));
  }, [slug]);

  if (loading) return <ScreenContainer><View style={styles.center}><ActivityIndicator color="#E60023" /></View></ScreenContainer>;
  if (!store) return <ScreenContainer><View style={styles.center}><Text>المتجر غير موجود</Text></View></ScreenContainer>;

  return <ScreenContainer edges={["top","bottom","left","right"]} className="bg-[#F5F5F5]">
    <View style={styles.header}><TouchableOpacity onPress={() => router.back()}><MaterialIcons name="arrow-forward" size={25} /></TouchableOpacity><Text style={styles.title}>{store.store_name}</Text><ShareButton type="store" id={store.slug} title={store.store_name} /></View>
    <FlatList
      data={products}
      numColumns={2}
      keyExtractor={item => item.id}
      contentContainerStyle={styles.list}
      columnWrapperStyle={styles.row}
      ListHeaderComponent={<View>
        <View style={styles.storeInfo}>{store.cover_url ? <Image source={{uri:store.cover_url}} style={styles.cover} /> : null}<View style={styles.logoPlaceholder}>{store.logo_url ? <Image source={{uri:store.logo_url}} style={styles.logoImage} /> : <MaterialIcons name="storefront" size={40} color="#E60023" />}</View><Text style={styles.storeName}>{store.store_name}</Text><View style={styles.rating}><MaterialIcons name="star" size={18} color="#F2B600" /><Text>4.8 · تقييم العملاء</Text></View><Text style={styles.storeDesc}>{store.description || "وصف المتجر سيظهر هنا."}</Text></View>
        {sections.map(section => <StorefrontSection key={section.id} section={section} />)}
        <Text style={styles.productsTitle}>منتجات المتجر ({products.length})</Text>
      </View>}
      renderItem={({ item }) => <View style={styles.productWrapper}><ProductCard product={item} /></View>}
      ListEmptyComponent={<Text style={styles.empty}>لا توجد منتجات منشورة في هذا المتجر.</Text>}
    />
  </ScreenContainer>;
}

function StorefrontSection({ section }: { section: StorefrontTab }) {
  const slide = section.slides[0];
  const circles = section.circles.filter(item => item.visible && item.isActive);
  const cards = section.cards.filter(item => item.visible && item.isActive);
  return <View style={styles.section}>
    {slide?.imageUrl ? <Pressable style={styles.hero} onPress={() => navigate(slide.url)}><Image source={{ uri: slide.imageUrl }} style={styles.heroImage} /><View style={styles.heroShade}/><View style={styles.heroText}>{slide.badge ? <Text style={styles.heroBadge}>{slide.badge}</Text> : null}<Text style={styles.heroTitle}>{slide.title}</Text>{slide.subtitle ? <Text style={styles.heroSub}>{slide.subtitle}</Text> : null}{slide.ctaLabel ? <View style={styles.heroButton}><Text style={styles.heroButtonText}>{slide.ctaLabel}</Text></View> : null}</View></Pressable> : null}
    {circles.length ? <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.circleRow}>{circles.map(circle => <Pressable key={circle.id} style={styles.circleItem} onPress={() => navigate(circle.url)}><View style={styles.circle}>{circle.imageUrl ? <Image source={{uri:circle.imageUrl}} style={StyleSheet.absoluteFillObject}/> : <MaterialIcons name="category" size={23} color="#777"/>}</View><Text numberOfLines={1} style={styles.circleText}>{circle.title}</Text></Pressable>)}</ScrollView> : null}
    {cards.length ? <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.cardRow}>{cards.map(card => <Pressable key={card.id} style={styles.card} onPress={() => navigate(card.url)}>{card.imageUrl ? <Image source={{uri:card.imageUrl}} style={styles.cardImage}/> : <View style={styles.cardImageFallback}><MaterialIcons name="image" size={26} color="#aaa"/></View>}<View style={styles.cardBody}>{card.badge ? <Text style={styles.cardBadge}>{card.badge}</Text> : null}<Text style={styles.cardTitle}>{card.title}</Text>{card.subtitle ? <Text numberOfLines={2} style={styles.cardSub}>{card.subtitle}</Text> : null}</View></Pressable>)}</ScrollView> : null}
  </View>;
}

function navigate(url: string) { const value = url.trim(); if (!value) return; if (value.startsWith("/")) router.push(value as never); }

const styles=StyleSheet.create({center:{flex:1,justifyContent:"center",alignItems:"center"},header:{height:54,paddingHorizontal:16,backgroundColor:"#FFF",flexDirection:"row",justifyContent:"space-between",alignItems:"center",borderBottomWidth:1,borderColor:"#F5F5F5"},title:{fontSize:16,fontWeight:"900",color:"#111"},storeInfo:{alignItems:"flex-end",padding:18,backgroundColor:"#FFF",marginBottom:12,borderRadius:12},cover:{width:"100%",height:120,borderRadius:10,marginBottom:12},logoPlaceholder:{width:72,height:72,borderRadius:36,backgroundColor:"#FFF",alignItems:"center",justifyContent:"center",marginBottom:8,borderWidth:1,borderColor:"#EEE",overflow:"hidden"},logoImage:{width:"100%",height:"100%"},storeName:{fontSize:20,fontWeight:"900",color:"#111"},rating:{flexDirection:"row",gap:5,alignItems:"center",marginTop:5},storeDesc:{color:"#777",textAlign:"right",fontSize:12,lineHeight:20,marginTop:8},productsTitle:{fontSize:16,fontWeight:"900",marginTop:16,marginBottom:8,textAlign:"right",paddingHorizontal:4},list:{padding:10},row:{justifyContent:"space-between",gap:10,marginBottom:10},productWrapper:{flex:1,maxWidth:"48%"},empty:{padding:40,textAlign:"center",color:"#777"},section:{marginBottom:10},hero:{height:210,borderRadius:15,overflow:"hidden",marginBottom:10,position:"relative",backgroundColor:"#eee"},heroImage:{width:"100%",height:"100%"},heroShade:{...StyleSheet.absoluteFillObject,backgroundColor:"rgba(0,0,0,.26)"},heroText:{position:"absolute",right:16,bottom:16,alignItems:"flex-end",maxWidth:"82%"},heroBadge:{backgroundColor:"#fff",paddingHorizontal:7,paddingVertical:4,borderRadius:99,fontSize:9,fontWeight:"900"},heroTitle:{color:"#fff",fontSize:22,fontWeight:"900",marginTop:7,textAlign:"right"},heroSub:{color:"#fff",fontSize:11,marginTop:4,textAlign:"right"},heroButton:{backgroundColor:"#fff",paddingHorizontal:12,paddingVertical:7,borderRadius:18,marginTop:8},heroButtonText:{fontSize:10,fontWeight:"900",color:"#111"},circleRow:{paddingHorizontal:4,gap:14,paddingVertical:8},circleItem:{width:66,alignItems:"center"},circle:{width:58,height:58,borderRadius:29,backgroundColor:"#fff",borderWidth:1,borderColor:"#eee",overflow:"hidden",alignItems:"center",justifyContent:"center"},circleText:{fontSize:9,color:"#333",fontWeight:"800",marginTop:5,textAlign:"center"},cardRow:{paddingHorizontal:2,gap:10,paddingVertical:4},card:{width:220,borderRadius:13,overflow:"hidden",backgroundColor:"#fff",borderWidth:1,borderColor:"#eee"},cardImage:{width:"100%",height:110},cardImageFallback:{width:"100%",height:110,backgroundColor:"#f0f0f0",alignItems:"center",justifyContent:"center"},cardBody:{padding:10,alignItems:"flex-end"},cardBadge:{fontSize:9,fontWeight:"900",color:"#8b5cf6"},cardTitle:{fontSize:13,fontWeight:"900",color:"#111",textAlign:"right"},cardSub:{fontSize:9,color:"#777",textAlign:"right",marginTop:3,lineHeight:15}});
