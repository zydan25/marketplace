import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { router } from "expo-router";
import { useMemo, useState } from "react";
import { Dimensions, Image, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { ProductCard } from "@/components/product-card";
import type { StoreProduct } from "@/lib/product-api";
import type { StorefrontTheme } from "@/lib/storefront-api";

export type DynamicSection = {
  id?: string | number;
  key?: string;
  type?: string;
  title?: string;
  sort_order?: number;
  is_visible?: boolean;
  config?: Record<string, any>;
};

type Category = { id: number; name: string; slug?: string; imageUrl?: string };
type RendererProps = { sections: DynamicSection[]; theme: StorefrontTheme | null; products: StoreProduct[]; categories: Category[] };
const width = Dimensions.get("window").width;

export function StorefrontRenderer({ sections, theme, products, categories, includeBottomNav = true }: RendererProps & { includeBottomNav?: boolean }) {
  const layout = theme?.layout ?? {};
  const tokens = theme?.tokens ?? {};
  const family = String(layout.family ?? "fashion");
  const primary = String(tokens.primary ?? (family === "electronics" ? "#0D47A1" : "#E60023"));
  const background = String(tokens.background ?? "#FFFFFF");
  const sectionGap = Math.max(0, Number(layout.section_gap ?? 8));
  const pagePadding = Math.max(0, Number(layout.page_padding ?? 0));
  const sorted = useMemo(() => [...sections].filter((s) => s.is_visible !== false).sort((a, b) => Number(a.sort_order ?? 0) - Number(b.sort_order ?? 0)), [sections]);
  const header = sorted.find((s) => String(s.type).toLowerCase() === "header");
  const bottomNav = sorted.find((s) => String(s.type).toLowerCase() === "bottom_nav");
  const body = sorted.filter((s) => String(s.type).toLowerCase() !== "bottom_nav");
  const heroIndex = body.findIndex((s) => ["hero", "banner"].includes(String(s.type).toLowerCase()));
  const headerOverlay = Boolean(header?.config?.overlay ?? layout.header_overlay ?? false) && family === "fashion" && heroIndex >= 0;
  const render = (section: DynamicSection) => <RenderSection key={String(section.id ?? section.key)} section={section} theme={theme} products={products} categories={categories} primary={primary} family={family} />;
  return <View style={[styles.root, { backgroundColor: background, paddingHorizontal: pagePadding }]}>
    {headerOverlay ? <View style={[styles.overlayStage, { marginHorizontal: -pagePadding }]}>{body.slice(heroIndex, heroIndex + 1).map(render)}<View style={styles.overlayHeader}>{render(header!)}</View></View> : null}
    {body.map((section, index) => { if (headerOverlay && index === heroIndex) return null; return <View key={String(section.id ?? section.key)} style={{ marginBottom: index === body.length - 1 ? 0 : sectionGap }}>{render(section)}</View>; })}
    {includeBottomNav && bottomNav ? <StorefrontBottomNavigation config={bottomNav.config ?? {}} primary={primary} preview /> : null}
  </View>;
}

export function StorefrontBottomNavigation({ config, primary }: { config: Record<string, any>; primary: string; preview?: boolean }) {
  const items = Array.isArray(config.items) && config.items.length ? config.items : [
    { label: "حسابي", icon: "person-outline", url: "/profile" },
    { label: "المفضلة", icon: "favorite-border", url: "/favorites" },
    { label: "السلة", icon: "shopping-cart", url: "/bag" },
    { label: "المنتجات", icon: "inventory-2", url: "/collection" },
    { label: "الرئيسية", icon: "home", url: "/" },
  ];
  const activeIndex = Math.max(0, Math.min(items.length - 1, Number(config.active_index ?? items.length - 1)));
  return <View style={[styles.bottomNav, config.style === "pill" && styles.bottomNavPill]}>{items.map((item: any, index: number) => <Pressable key={`${String(item.label)}-${index}`} style={[styles.bottomItem, index === activeIndex && styles.bottomActive]} onPress={() => navigateUrl(String(item.url ?? ""))}><MaterialIcons name={item.icon || "circle"} size={22} color={index === activeIndex ? primary : "#607080"} /><Text style={[styles.bottomText, index === activeIndex && { color: primary }]}>{String(item.label ?? "")}</Text></Pressable>)}</View>;
}

type SectionRendererProps = Omit<RendererProps, "sections"> & { section: DynamicSection; primary: string; family: string };
function RenderSection({ section, theme, products, categories, primary, family }: SectionRendererProps) {
  const config = section.config ?? {};
  const type = String(section.type ?? "").toLowerCase();
  switch (type) {
    case "header": return <Header config={config} categories={categories} primary={primary} family={family} />;
    case "hero": case "banner": return <Hero section={section} primary={primary} theme={theme} family={family} />;
    case "promo_strip": return <PromoStrip config={config} primary={primary} theme={theme} />;
    case "notice": return <Notice config={config} primary={primary} />;
    case "category_bar": return <CategoryBar config={config} categories={categories} primary={primary} />;
    case "category_grid": case "category": return <CategoryGrid title={section.title} config={config} categories={categories} primary={primary} theme={theme} />;
    case "brand_grid": return <BrandGrid title={section.title} config={config} products={products} primary={primary} />;
    case "tabs": case "tab": return <BrowseTabs config={config} primary={primary} />;
    case "catalog_toolbar": return <CatalogToolbar title={section.title} config={config} itemsCount={countProducts(config, products)} primary={primary} />;
    case "product_grid": case "trend": return <ProductGrid section={section} products={products} primary={primary} theme={theme} />;
    default: return null;
  }
}

function Header({ config, categories, primary, family }: { config: Record<string, any>; categories: Category[]; primary: string; family: string }) {
  const chips = categories.slice(0, Math.max(1, Number(config.category_chip_limit ?? (family === "electronics" ? 6 : 7))));
  if (family === "electronics") return <View style={[styles.electronicsHeader, { backgroundColor: primary }]}>
    <View style={styles.electronicsTop}>
      {config.show_notifications !== false ? <IconButton name="notifications-none" color="#FFF" /> : null}
      <View style={styles.electronicsSearch}><Text numberOfLines={1} style={styles.electronicsSearchText}>{String(config.search_placeholder ?? "ابحث عن منتج أو متجر")}</Text><MaterialIcons name="search" size={22} color={primary} /></View>
      {config.show_account !== false ? <IconButton name="account-circle" color="#FFF" /> : null}
    </View>
    {config.show_category_nav !== false ? <ScrollView horizontal inverted showsHorizontalScrollIndicator={false} contentContainerStyle={styles.electronicsNav}>{chips.map((item) => <Pressable key={item.id} onPress={() => openCategory(item)} style={styles.electronicsNavItem}><Text style={styles.electronicsNavText}>{item.name}</Text></Pressable>)}</ScrollView> : null}
  </View>;
  return <View style={styles.fashionHeader}>
    <View style={styles.fashionTop}>
      <View style={styles.fashionIconRow}>{config.show_mail !== false ? <IconButton name="mail-outline"/> : null}{config.show_calendar !== false ? <IconButton name="calendar-today"/> : null}</View>
      <View style={styles.fashionSearch}><Text numberOfLines={1} style={styles.fashionSearchText}>{String(config.search_placeholder ?? "ابحث عن منتج أو متجر")}</Text>{config.show_camera !== false ? <MaterialIcons name="camera-alt" size={18} color="#777"/> : null}<View style={styles.searchButton}><MaterialIcons name="search" size={20} color="#FFF"/></View></View>
      {config.show_favorites !== false ? <IconButton name="favorite-border" badge={String(config.favorite_badge ?? "3")}/> : null}
    </View>
    {config.show_category_chips !== false ? <ScrollView horizontal inverted showsHorizontalScrollIndicator={false} contentContainerStyle={styles.fashionNav}>{chips.map((item,index)=><Pressable key={item.id} onPress={()=>openCategory(item)} style={index===0?styles.fashionNavActive:styles.fashionNavItem}><Text style={index===0?styles.fashionNavActiveText:[styles.fashionNavText,{color:primary}]}>{index===0?`كل  ${item.name}`:item.name}</Text></Pressable>)}</ScrollView>:null}
  </View>;
}
function IconButton({name,color="#111",badge}:{name:any;color?:string;badge?:string}){return <View style={styles.iconButton}><MaterialIcons name={name} size={23} color={color}/>{badge?<View style={styles.iconBadge}><Text style={styles.iconBadgeText}>{badge}</Text></View>:null}</View>}

function Hero({section,primary,theme,family}:{section:DynamicSection;primary:string;theme:StorefrontTheme|null;family:string}){
  const slides=Array.isArray(section.config?.slides)?section.config.slides.filter((x:any)=>x?.visible!==false&&x?.isActive!==false):[];
  const [index,setIndex]=useState(0);const slide=slides[Math.min(index,Math.max(0,slides.length-1))]??slides[0];if(!slide)return null;
  const height=Math.max(170,Number(section.config?.height??theme?.layout?.hero_height??(family==="electronics"?220:310)));const radius=Math.max(0,Number(section.config?.radius??theme?.layout?.hero_radius??0));const image=String(slide.imageUrl??slide.image_url??"");
  const overlay=Boolean(section.config?.overlay??(family==="fashion"));const opacity=Math.min(.9,Math.max(0,Number(section.config?.overlay_opacity??(overlay?.3:0))));
  return <View style={[styles.heroWrap,{height}]}><Pressable style={[styles.hero,{borderRadius:radius}]} onPress={()=>navigateUrl(String(slide.url??""))}>{image?<Image source={{uri:image}} style={StyleSheet.absoluteFillObject} resizeMode={String(section.config?.image_fit??"cover") as any}/>:<View style={styles.heroEmpty}><MaterialIcons name="image" size={42} color="#AAA"/><Text style={styles.heroEmptyText}>أضف البانر من محرر التصميم</Text></View>}{overlay?<View style={[styles.heroShade,{backgroundColor:`rgba(0,0,0,${opacity})`}]}/>:null}<View style={[styles.heroText,{alignItems:String(section.config?.text_align??"right")==="left"?"flex-start":"flex-end"}]}>{slide.badge?<Text style={styles.heroBadge}>{slide.badge}</Text>:null}{slide.title?<Text style={styles.heroTitle}>{slide.title}</Text>:null}{slide.subtitle?<Text style={styles.heroSubtitle}>{slide.subtitle}</Text>:null}{slide.ctaLabel?<View style={[styles.heroButton,{borderColor:primary}]}><Text style={styles.heroButtonText}>{slide.ctaLabel}</Text><MaterialIcons name="arrow-back" size={16} color="#111"/></View>:null}</View></Pressable>{slides.length>1&&section.config?.show_dots!==false?<View style={styles.dots}>{slides.map((item:any,i:number)=><Pressable key={String(item.id??i)} onPress={()=>setIndex(i)} style={[styles.dot,{backgroundColor:i===index?primary:"#B8B8B8"}]}/>)}</View>:null}</View>
}
function PromoStrip({config,primary,theme}:{config:Record<string,any>;primary:string;theme:StorefrontTheme|null}){const items=Array.isArray(config.items)?config.items:[];const columns=Math.max(1,Number(config.columns??Math.min(3,items.length||3)));return <View style={[styles.promoStrip,{backgroundColor:String(config.background??theme?.tokens?.surface??"#FFF"),borderRadius:Number(config.radius??0)}]}>{items.slice(0,columns).map((item:any,index:number)=><View key={String(item.id??index)} style={[styles.promoCell,index<Math.min(items.length,columns)-1&&styles.promoDivider]}><Text style={[styles.promoTitle,{color:String(item.titleColor??primary)}]}>{String(item.title??"")}</Text><Text style={styles.promoValue}>{String(item.value??"")}</Text>{item.note?<Text style={styles.promoNote}>{String(item.note)}</Text>:null}</View>)}</View>}
function Notice({config,primary}:{config:Record<string,any>;primary:string}){return <View style={[styles.notice,{backgroundColor:String(config.background??"#FFFDF4")}]}><View style={[styles.noticeLine,{backgroundColor:primary}]}/><Text style={styles.noticeText}>{String(config.text??"")}</Text></View>}
function CategoryBar({config,categories,primary}:{config:Record<string,any>;categories:Category[];primary:string}){return <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.categoryBar}>{categories.slice(0,Math.max(1,Number(config.limit??10))).map((item)=><Pressable key={item.id} onPress={()=>openCategory(item)} style={[styles.categoryBarChip,{borderColor:`${primary}35`}]}><Text style={[styles.categoryBarText,{color:primary}]}>{item.name}</Text></Pressable>)}</ScrollView>}
function CategoryGrid({title,config,categories,primary,theme}:{title?:string;config:Record<string,any>;categories:Category[];primary:string;theme:StorefrontTheme|null}){
  const family=String(theme?.layout?.family??"");const columns=Math.max(1,Number(config.columns??(family==="electronics"?4:5)));const rows=Math.max(1,Number(config.rows??3));const size=Math.max(42,Number(config.size??theme?.layout?.category_size??68));const gap=Math.max(4,Number(config.gap??theme?.layout?.category_gap??12));const horizontal=Boolean(config.horizontal);const count=horizontal?Math.max(columns,Number(config.limit??columns)):rows*columns;const items=categories.slice(0,count);const labelLines=Math.max(1,Number(config.label_lines??(family==="electronics"?2:1)));
  const card=(category:Category,wide=false)=><Pressable key={category.id} style={{width:wide?Math.max(size+24,86):`${100/columns}%`}} onPress={()=>openCategory(category)}><View style={[styles.categoryVisual,{width:size,height:size,borderRadius:size/2,backgroundColor:String(config.background??"#F4F4F4"),borderColor:`${primary}18`,alignSelf:"center"}]}>{category.imageUrl?<Image source={{uri:category.imageUrl}} style={StyleSheet.absoluteFillObject} resizeMode={String(config.image_fit??"cover") as any}/>:<MaterialIcons name="category" size={Math.round(size*.34)} color={primary}/>}</View><Text numberOfLines={labelLines} style={[styles.categoryLabel,{fontSize:Number(config.label_size??10),color:String(config.label_color??"#444")}]}>{category.name}</Text></Pressable>;
  return <View style={styles.sectionCard}>{config.show_title!==false&&title?<SectionTitle title={title} primary={primary} subtitle={config.title_note}/>:null}{horizontal?<ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{paddingHorizontal:3,gap}}>{items.map((x)=>card(x,true))}</ScrollView>:<View style={[styles.categoryGrid,{columnGap:gap,rowGap:gap}]}>{items.map((x)=>card(x))}</View>}</View>
}
function BrandGrid({title,config,products,primary}:{title?:string;config:Record<string,any>;products:StoreProduct[];primary:string}){const limit=Math.max(1,Number(config.limit??8));const columns=Math.max(1,Number(config.columns??4));const size=Math.max(48,Number(config.size??84));const rows=Math.max(1,Number(config.rows??Math.ceil(limit/columns)));const brands:Array<{name:string;image:string}>=[];const seen=new Set<string>();for(const product of products){const name=String((product as any).brand??"").trim();if(!name||seen.has(name))continue;seen.add(name);brands.push({name,image:product.images[0]?.url??""});if(brands.length>=limit)break;}return <View style={styles.sectionCard}>{title?<SectionTitle title={title} primary={primary}/>:null}<View style={[styles.brandGrid,{columnGap:Number(config.gap??16),rowGap:Number(config.gap??16)}]}>{brands.slice(0,rows*columns).map((brand)=><Pressable key={brand.name} style={{width:`${100/columns}%`}} onPress={()=>router.push(`/collection?brand=${encodeURIComponent(brand.name)}` as never)}><View style={[styles.brandVisual,{width:size,height:size,borderRadius:size/2,borderColor:`${primary}25`}]}>{brand.image?<Image source={{uri:brand.image}} style={StyleSheet.absoluteFillObject} resizeMode="cover"/>:<MaterialIcons name="store" size={28} color={primary}/>}</View><Text style={styles.brandLabel}>{brand.name}</Text></Pressable>)}</View></View>}
function BrowseTabs({config,primary}:{config:Record<string,any>;primary:string}){const items=Array.isArray(config.items)?config.items:Array.isArray(config.tabs)?config.tabs:[];const active=Math.max(0,Math.min(items.length-1,Number(config.active_index??items.length-1)));return <ScrollView horizontal inverted showsHorizontalScrollIndicator={false} contentContainerStyle={styles.browseTabs}>{items.map((item:any,index:number)=><Pressable key={String(item.id??index)} onPress={()=>navigateUrl(String(item.url??""))} style={[styles.browseTab,index===active&&{backgroundColor:primary}]}><Text style={[styles.browseTabText,index===active&&{color:"#FFF"}]}>{String(item.title??item.label??"")}</Text></Pressable>)}</ScrollView>}
function CatalogToolbar({title,config,itemsCount,primary}:{title?:string;config:Record<string,any>;itemsCount:number;primary:string}){return <View style={styles.toolbar}><View style={styles.toolbarTitleWrap}>{config.show_count!==false?<Text style={styles.count}>{itemsCount} قطعة</Text>:null}{title?<Text style={styles.toolbarTitle}>{title}</Text>:null}</View><View style={styles.toolbarActions}>{config.show_sort!==false?<View style={styles.toolbarButton}><MaterialIcons name="sort" size={16} color={primary}/><Text style={styles.toolbarText}>الترتيب</Text></View>:null}{config.show_filter!==false?<View style={styles.toolbarButton}><MaterialIcons name="tune" size={16} color={primary}/><Text style={styles.toolbarText}>تصفية</Text></View>:null}</View></View>}
function ProductGrid({section,products,primary,theme}:{section:DynamicSection;products:StoreProduct[];primary:string;theme:StorefrontTheme|null}){const c=section.config??{};const cols=Math.max(1,Number(c.columns_mobile??theme?.layout?.product_columns_mobile??2));const rows=Math.max(1,Number(c.rows??2));const limit=Math.max(1,Number(c.limit??cols*rows));const source=String(c.source??(section.type==="trend"?"trending":"latest")).toLowerCase();let list=[...products];if(["discounts","deals","offers"].includes(source))list=list.filter(x=>x.discountPercent>0);if(["trending","trend"].includes(source))list=list.filter(x=>x.isTrending);if(["best_selling","bestsellers","most_sold"].includes(source))list.sort((a,b)=>Number((b as any).sold_count??0)-Number((a as any).sold_count??0));if(Array.isArray(c.product_ids)&&c.product_ids.length){const ids=new Set(c.product_ids.map(String));list=list.filter(x=>ids.has(String(x.id)));}const chosen=list.slice(0,Math.min(limit,cols*rows));const gap=Math.max(4,Number(c.gap??theme?.layout?.product_gap??10));return <View style={styles.productsSection}><View style={styles.sectionTitleRow}>{section.title?<Text style={styles.sectionTitle}>{section.title}</Text>:<View/>}{c.show_see_all!==false?<Pressable onPress={()=>router.push("/collection" as never)}><Text style={[styles.seeAll,{color:primary}]}>عرض الكل</Text></Pressable>:null}</View><View style={[styles.productGrid,{marginHorizontal:-gap/2}]}>{chosen.map(product=><View key={product.id} style={{width:`${100/cols}%`,paddingHorizontal:gap/2,marginBottom:gap}}><ProductCard product={product}/></View>)}</View></View>}
function SectionTitle({title,primary,subtitle}:{title:string;primary:string;subtitle?:string}){return <View style={styles.sectionTitleBlock}><View style={styles.sectionTitleRow}><View style={[styles.titleMark,{backgroundColor:primary}]}/><Text style={styles.sectionTitle}>{title}</Text></View>{subtitle?<Text style={styles.sectionSubtitle}>{subtitle}</Text>:null}</View>}
function countProducts(config:Record<string,any>,products:StoreProduct[]){const source=String(config.source??"latest").toLowerCase();if(["discounts","deals","offers"].includes(source))return products.filter(x=>x.discountPercent>0).length;if(["trending","trend"].includes(source))return products.filter(x=>x.isTrending).length;return products.length}
function openCategory(category:Category){router.push(`/collection?category=${encodeURIComponent(category.slug??category.name)}` as never)}
function navigateUrl(url:string){const value=url.trim();if(value.startsWith("/"))router.push(value as never)}

const styles=StyleSheet.create({
  root:{width:"100%"},overlayStage:{position:"relative",width:"100%"},overlayHeader:{position:"absolute",top:0,left:0,right:0,zIndex:20},previewBottomNav:{minHeight:74,justifyContent:"flex-end"},
  fashionHeader:{paddingTop:8,paddingBottom:3,backgroundColor:"transparent"},fashionTop:{minHeight:56,flexDirection:"row-reverse",alignItems:"center",gap:7,paddingHorizontal:10},fashionIconRow:{flexDirection:"row-reverse",gap:3},fashionSearch:{flex:1,minHeight:45,backgroundColor:"#FFF",borderRadius:24,flexDirection:"row-reverse",alignItems:"center",paddingLeft:6,paddingRight:13,gap:9,elevation:3,shadowOpacity:.1,shadowRadius:8,shadowOffset:{width:0,height:3}},fashionSearchText:{flex:1,color:"#444",fontSize:12,fontWeight:"700",textAlign:"right"},searchButton:{width:36,height:36,borderRadius:18,backgroundColor:"#101828",alignItems:"center",justifyContent:"center"},fashionNav:{paddingHorizontal:9,gap:14,alignItems:"center"},fashionNavItem:{paddingVertical:9},fashionNavText:{fontSize:11,fontWeight:"800"},fashionNavActive:{paddingVertical:9,borderBottomWidth:3,borderBottomColor:"#E60023"},fashionNavActiveText:{fontSize:11,fontWeight:"900",color:"#111"},
  electronicsHeader:{minHeight:102,paddingTop:8,paddingBottom:5},electronicsTop:{height:49,flexDirection:"row-reverse",alignItems:"center",paddingHorizontal:10,gap:9},electronicsSearch:{flex:1,height:38,backgroundColor:"#FFF",flexDirection:"row-reverse",alignItems:"center",paddingHorizontal:9,gap:7},electronicsSearchText:{flex:1,color:"#777",fontSize:11,textAlign:"right"},electronicsNav:{paddingHorizontal:10,gap:20,alignItems:"center",minHeight:38},electronicsNavItem:{paddingVertical:8},electronicsNavText:{color:"#FFF",fontSize:12,fontWeight:"900"},
  iconButton:{width:35,height:35,alignItems:"center",justifyContent:"center",position:"relative"},iconBadge:{position:"absolute",right:1,top:-2,minWidth:15,height:15,borderRadius:9,backgroundColor:"#E60023",alignItems:"center",justifyContent:"center",paddingHorizontal:3},iconBadgeText:{color:"#FFF",fontSize:8,fontWeight:"900"},
  heroWrap:{width:"100%"},hero:{width:"100%",height:"100%",overflow:"hidden",backgroundColor:"#F1F1F1",position:"relative"},heroShade:{...StyleSheet.absoluteFillObject},heroEmpty:{flex:1,alignItems:"center",justifyContent:"center"},heroEmptyText:{color:"#777",fontSize:11,marginTop:8},heroText:{position:"absolute",right:18,left:18,bottom:18},heroBadge:{alignSelf:"flex-end",color:"#111",backgroundColor:"#FFF",borderRadius:99,paddingHorizontal:9,paddingVertical:4,fontSize:9,fontWeight:"900"},heroTitle:{color:"#FFF",fontSize:width>700?30:23,fontWeight:"900",textAlign:"right",marginTop:6},heroSubtitle:{color:"#FFF",fontSize:12,textAlign:"right",marginTop:3},heroButton:{alignSelf:"flex-end",marginTop:9,backgroundColor:"#FFF",borderWidth:1,borderRadius:22,paddingHorizontal:14,paddingVertical:9,flexDirection:"row-reverse",alignItems:"center",gap:6},heroButtonText:{color:"#111",fontSize:11,fontWeight:"900"},dots:{flexDirection:"row",justifyContent:"center",alignItems:"center",gap:6,paddingVertical:7},dot:{width:7,height:7,borderRadius:4},
  promoStrip:{width:"100%",minHeight:76,flexDirection:"row-reverse",borderWidth:1,borderColor:"#F0F0F0",overflow:"hidden"},promoCell:{flex:1,alignItems:"center",justifyContent:"center",paddingHorizontal:7,paddingVertical:8},promoDivider:{borderLeftWidth:1,borderLeftColor:"#EEE"},promoTitle:{fontSize:11,fontWeight:"900",textAlign:"center"},promoValue:{fontSize:10,color:"#555",fontWeight:"700",marginTop:2,textAlign:"center"},promoNote:{fontSize:7,color:"#999",marginTop:1,textAlign:"center"},notice:{minHeight:58,flexDirection:"row-reverse",alignItems:"center",paddingHorizontal:14,gap:9},noticeLine:{width:5,height:28,borderRadius:3},noticeText:{flex:1,color:"#222",fontSize:12,lineHeight:21,fontWeight:"800",textAlign:"center"},
  categoryBar:{paddingHorizontal:11,gap:8,paddingVertical:8},categoryBarChip:{paddingHorizontal:13,paddingVertical:7,borderWidth:1,borderRadius:999,backgroundColor:"#FFF"},categoryBarText:{fontSize:10,fontWeight:"900"},sectionCard:{backgroundColor:"#FFF",paddingVertical:8,paddingHorizontal:11},categoryGrid:{flexDirection:"row-reverse",flexWrap:"wrap",alignItems:"flex-start"},categoryVisual:{overflow:"hidden",alignItems:"center",justifyContent:"center",borderWidth:1},categoryLabel:{marginTop:5,textAlign:"center",fontWeight:"800",paddingHorizontal:2},sectionTitleBlock:{marginBottom:2},sectionTitleRow:{minHeight:34,flexDirection:"row-reverse",alignItems:"center",justifyContent:"space-between",paddingHorizontal:3,gap:7},titleMark:{width:6,height:20,borderRadius:3},sectionTitle:{flex:1,color:"#111",fontSize:13,fontWeight:"900",textAlign:"right"},sectionSubtitle:{color:"#8A8A8A",fontSize:9,textAlign:"right",paddingHorizontal:4,marginBottom:5},
  brandGrid:{flexDirection:"row-reverse",flexWrap:"wrap",alignItems:"flex-start"},brandVisual:{overflow:"hidden",borderWidth:1,alignSelf:"center",backgroundColor:"#FFF",alignItems:"center",justifyContent:"center"},brandLabel:{textAlign:"center",marginTop:5,fontSize:10,fontWeight:"800",color:"#444"},browseTabs:{paddingHorizontal:10,gap:7,paddingVertical:7},browseTab:{paddingHorizontal:14,paddingVertical:8,borderRadius:99,backgroundColor:"#F4F4F4"},browseTabText:{color:"#333",fontSize:10,fontWeight:"900"},
  toolbar:{minHeight:48,flexDirection:"row-reverse",alignItems:"center",justifyContent:"space-between",paddingHorizontal:11,backgroundColor:"#FFF",borderTopWidth:1,borderBottomWidth:1,borderColor:"#EFEFEF"},toolbarTitleWrap:{flexDirection:"row-reverse",alignItems:"center",gap:7},toolbarTitle:{color:"#222",fontSize:13,fontWeight:"900"},count:{color:"#999",fontSize:9},toolbarActions:{flexDirection:"row-reverse",gap:7},toolbarButton:{flexDirection:"row-reverse",gap:4,alignItems:"center",paddingHorizontal:8,paddingVertical:6,borderRadius:9,backgroundColor:"#F7F7F7"},toolbarText:{fontSize:9,color:"#555",fontWeight:"800"},
  productsSection:{paddingHorizontal:9,paddingVertical:5,backgroundColor:"#FFF"},seeAll:{fontSize:10,fontWeight:"900"},productGrid:{flexDirection:"row-reverse",flexWrap:"wrap"},discountLine:{fontSize:8,fontWeight:"900",textAlign:"right",paddingHorizontal:5},
  bottomNav:{height:68,backgroundColor:"#FFF",borderTopWidth:1,borderTopColor:"#E7E7E7",flexDirection:"row-reverse",alignItems:"center",justifyContent:"space-around",paddingHorizontal:5},bottomNavPill:{marginHorizontal:8,borderRadius:20,borderWidth:1,borderColor:"#ECECEC"},bottomItem:{minWidth:48,height:58,alignItems:"center",justifyContent:"center",gap:2},bottomActive:{width:58,height:58,borderRadius:29,backgroundColor:"#EEF4FF"},bottomText:{fontSize:8,color:"#607080",fontWeight:"800"},
});
