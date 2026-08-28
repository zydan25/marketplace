import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { useEffect, useState } from "react";
import { ActivityIndicator, FlatList, Image, Pressable, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";

import { ScreenContainer } from "@/components/screen-container";
import { ProductCard } from "@/components/product-card";
import { ShareButton } from "@/components/share-button";
import { apiCall } from "@/lib/_core/api";
import { getProducts, type StoreProduct } from "@/lib/product-api";

type RawSection = { id: number | string; type?: string; section_type?: string; title?: string; sort_order?: number; config?: Record<string, any>; is_visible?: boolean };
type StorePayload = { store?: { id?: number | null; store_name?: string; slug?: string; description?: string; logo_url?: string | null; cover_url?: string | null } | null; theme?: { tokens?: Record<string, any>; layout?: Record<string, any> } | null; data?: RawSection[] };

export default function StoreScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const [payload, setPayload] = useState<StorePayload | null>(null);
  const [products, setProducts] = useState<StoreProduct[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!slug) return;
    Promise.all([apiCall<StorePayload>(`/api/stores/${encodeURIComponent(String(slug))}/home/`), getProducts()])
      .then(([home, all]) => { setPayload(home); setProducts(all.filter(item => item.vendor.slug === slug)); })
      .catch(() => undefined).finally(() => setLoading(false));
  }, [slug]);
  const store = payload?.store;
  const sections = (payload?.data ?? []).filter(section => section.is_visible !== false).sort((a,b)=>Number(a.sort_order??0)-Number(b.sort_order??0));
  const primary = String(payload?.theme?.tokens?.primary ?? "#E60023");
  const background = String(payload?.theme?.tokens?.background ?? "#F5F5F5");
  if (loading) return <ScreenContainer><View style={styles.center}><ActivityIndicator color="#E60023"/></View></ScreenContainer>;
  if (!store) return <ScreenContainer><View style={styles.center}><Text>المتجر غير موجود أو غير نشط.</Text></View></ScreenContainer>;
  return <ScreenContainer edges={["top","bottom","left","right"]} style={{backgroundColor:background}}>
    <View style={styles.header}><TouchableOpacity onPress={()=>router.back()}><MaterialIcons name="arrow-forward" size={25} color="#111"/></TouchableOpacity><Text style={styles.title}>{store.store_name}</Text><ShareButton type="store" id={String(store.slug??slug)} title={store.store_name??"متجر"}/></View>
    <FlatList data={products} numColumns={2} keyExtractor={item=>String(item.id)} contentContainerStyle={styles.list} columnWrapperStyle={styles.row}
      ListHeaderComponent={<View><View style={styles.storeInfo}>{store.cover_url?<Image source={{uri:store.cover_url}} style={styles.cover}/>:null}<View style={styles.logo}>{store.logo_url?<Image source={{uri:store.logo_url}} style={styles.logoImage}/>:<MaterialIcons name="storefront" size={36} color={primary}/>}</View><Text style={styles.storeName}>{store.store_name}</Text>{store.description?<Text style={styles.storeDesc}>{store.description}</Text>:null}</View>{sections.map(section=><StorefrontSection key={String(section.id)} section={section} products={products} primary={primary}/>)}</View>}
      renderItem={({item})=><View style={styles.productWrapper}><ProductCard product={item}/></View>}
      ListEmptyComponent={<Text style={styles.empty}>لا توجد منتجات منشورة في هذا المتجر.</Text>}/>
    />
  </ScreenContainer>;
}

function StorefrontSection({section,products,primary}:{section:RawSection;products:StoreProduct[];primary:string}){
 const type=String(section.section_type??section.type??""); const config=section.config??{};
 const slides=Array.isArray(config.slides)?config.slides.filter((x:any)=>x?.visible!==false&&x?.isActive!==false):[];
 const circles=Array.isArray(config.circles)?config.circles.filter((x:any)=>x?.visible!==false&&x?.isActive!==false):[];
 const embeddedCircles=Array.isArray(config.category_circles)?config.category_circles.filter((x:any)=>x?.visible!==false&&x?.isActive!==false):[];
 const productRows=Array.isArray(config.products)?config.products:[]; const ids=productRows.map((x:any)=>Number(x?.id)).filter(Number.isFinite);
 const displayed=ids.length?ids.map((id:number)=>products.find(p=>Number(p.id)===id)).filter(Boolean) as StoreProduct[]:products.slice(0,Math.max(2,Number(config.rows??2)*Number(config.columns??2)*3));
 const columns=Math.max(2,Math.min(4,Number(config.columns??2))); const rows=Math.max(1,Math.min(6,Number(config.rows??2))); const scroll=config.scroll!==false;
 if(!["hero","banner","category","product_grid","trend"].includes(type))return null;
 return <View style={styles.section}>
   {slides.length?<ScrollView horizontal pagingEnabled showsHorizontalScrollIndicator={false} contentContainerStyle={styles.heroRow}>{slides.map((slide:any,index:number)=><Pressable key={String(slide.id??index)} style={styles.hero} onPress={()=>navigate(slide.url)}><Image source={{uri:String(slide.imageUrl??slide.image_url??"")}} style={styles.heroImage}/><View style={styles.heroShade}/><View style={styles.heroText}>{slide.badge?<Text style={styles.heroBadge}>{String(slide.badge)}</Text>:null}<Text style={styles.heroTitle}>{String(slide.title??section.title??"")}</Text>{slide.subtitle?<Text style={styles.heroSub}>{String(slide.subtitle)}</Text>:null}{slide.ctaLabel?<View style={[styles.heroButton,{borderColor:primary}]}><Text style={styles.heroButtonText}>{String(slide.ctaLabel)}</Text></View>:null}</View></Pressable>)}</ScrollView>:null}
   {type==="category"&&circles.length?<ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.circleRow}>{circles.map((circle:any,index:number)=><CategoryCircle key={String(circle.id??index)} circle={circle} primary={primary}/>)}</ScrollView>:null}
   {(type==="product_grid"||type==="trend")&&displayed.length?<View style={styles.gridSection}><View style={styles.sectionHeader}><Text style={styles.sectionTitle}>{section.title||(type==="trend"?"الأكثر رواجًا":"منتجات مختارة")}</Text><View style={[styles.sectionAccent,{backgroundColor:primary}]}/></View>{config.show_categories&&embeddedCircles.length?<ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.embeddedCircleRow}>{embeddedCircles.map((circle:any,index:number)=><CategoryCircle key={String(circle.id??index)} circle={circle} primary={primary}/>)}</ScrollView>:null}{scroll?<ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.productScroll}>{chunk(displayed.slice(0,rows*columns*3),rows).map((column,index)=><View key={index} style={styles.productColumn}>{column.map(product=><View key={String(product.id)} style={{width:160}}><ProductCard product={product}/></View>)}</View>)}</ScrollView>:<View style={styles.productGrid}>{displayed.slice(0,rows*columns).map(product=><View key={String(product.id)} style={{width:`${100/columns-2}%`}}><ProductCard product={product}/></View>)}</View>}</View>:null}
 </View>;
}
function chunk<T>(items:T[],size:number){const out:T[][]=[];for(let i=0;i<items.length;i+=size)out.push(items.slice(i,i+size));return out;}
function CategoryCircle({circle,primary}:{circle:any;primary:string}){return <Pressable style={styles.circleItem} onPress={()=>navigate(circle.url??`/collection?category=${encodeURIComponent(String(circle.targetCategory??""))}`)}><View style={[styles.circle,{borderColor:`${primary}30`]}>{circle.imageUrl?<Image source={{uri:String(circle.imageUrl)}} style={StyleSheet.absoluteFillObject}/>:<MaterialIcons name="category" size={24} color={primary}/>}</View><Text numberOfLines={1} style={styles.circleText}>{String(circle.title??circle.name??"")}</Text></Pressable>}
function navigate(url?:string){const value=String(url??"").trim();if(value.startsWith("/"))router.push(value as never);}
const styles=StyleSheet.create({center:{flex:1,alignItems:"center",justifyContent:"center"},header:{height:56,paddingHorizontal:16,backgroundColor:"#FFF",flexDirection:"row",justifyContent:"space-between",alignItems:"center",borderBottomWidth:1,borderColor:"#F0F0F0"},title:{fontSize:16,fontWeight:"900",color:"#111"},list:{padding:10,paddingBottom:60},row:{justifyContent:"space-between",gap:10,marginBottom:10},productWrapper:{flex:1,maxWidth:"48%"},storeInfo:{alignItems:"flex-end",padding:14,backgroundColor:"#FFF",borderRadius:14,marginBottom:10},cover:{width:"100%",height:150,borderRadius:12,marginBottom:12,backgroundColor:"#EEE"},logo:{width:76,height:76,borderRadius:38,backgroundColor:"#FFF",borderWidth:2,borderColor:"#F2F2F2",overflow:"hidden",justifyContent:"center",alignItems:"center",marginBottom:8},logoImage:{width:"100%",height:"100%"},storeName:{fontSize:21,fontWeight:"900",color:"#111"},storeDesc:{textAlign:"right",color:"#666",fontSize:12,lineHeight:19,marginTop:7},section:{backgroundColor:"transparent",marginBottom:8},heroRow:{gap:10},hero:{height:215,width:350,borderRadius:16,overflow:"hidden",backgroundColor:"#EEE",position:"relative"},heroImage:{width:"100%",height:"100%"},heroShade:{...StyleSheet.absoluteFillObject,backgroundColor:"rgba(0,0,0,0.28)"},heroText:{position:"absolute",right:16,bottom:16,maxWidth:"82%",alignItems:"flex-end"},heroBadge:{backgroundColor:"#FFF",color:"#111",paddingHorizontal:8,paddingVertical:4,borderRadius:50,fontSize:9,fontWeight:"900"},heroTitle:{color:"#FFF",fontSize:22,fontWeight:"900",marginTop:7,textAlign:"right"},heroSub:{color:"#FFF",fontSize:11,lineHeight:17,marginTop:4,textAlign:"right"},heroButton:{backgroundColor:"#FFF",borderWidth:1,paddingHorizontal:12,paddingVertical:7,borderRadius:20,marginTop:8},heroButtonText:{color:"#111",fontSize:10,fontWeight:"900"},circleRow:{paddingVertical:8,gap:14},embeddedCircleRow:{paddingVertical:7,gap:12},circleItem:{width:68,alignItems:"center"},circle:{width:60,height:60,borderRadius:30,borderWidth:2,backgroundColor:"#FFF",overflow:"hidden",alignItems:"center",justifyContent:"center"},circleText:{maxWidth:66,color:"#333",fontSize:9,fontWeight:"800",marginTop:5,textAlign:"center"},gridSection:{backgroundColor:"#FFF",borderRadius:14,padding:10},sectionHeader:{flexDirection:"row-reverse",alignItems:"center",justifyContent:"space-between",marginBottom:6},sectionTitle:{color:"#111",fontSize:16,fontWeight:"900"},sectionAccent:{width:28,height:4,borderRadius:2},productScroll:{gap:9},productColumn:{gap:9},productGrid:{flexDirection:"row-reverse",flexWrap:"wrap",justifyContent:"space-between",rowGap:10},empty:{color:"#888",textAlign:"center",padding:30}});
