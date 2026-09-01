import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ActivityIndicator, Alert, RefreshControl, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AdminLayout, Colors, Font, Shadow, Spacing } from "@/components/admin";
import { djangoApi } from "@/lib/django-api";

const PRESET_META = {
  fashion: { title: "التصميم الجاهز الأول — الأزياء", subtitle: "هيدر عائم، Hero كبير، عروض، فئات دائرية، تبويبات وشبكة منتجات.", accent: "#E60023", bg: "#FFF8FA" },
  electronics: { title: "التصميم الجاهز الثاني — الإلكترونيات", subtitle: "هيدر أزرق، بانر عريض، رسالة عروض، فئات، ماركات وشبكة منتجات.", accent: "#0D47A1", bg: "#F5F8FF" },
} as const;

type Theme = { id:number; name:string; is_global:boolean; is_active:boolean; tokens:Record<string,any>; layout:Record<string,any>; sections:Record<string,any>[] };
type Preset = { name:string; description?:string; tokens:Record<string,any>; layout:Record<string,any>; sections:Record<string,any>[] };
type PresetsResponse = Record<string, Preset>;

export default function ThemeLibraryScreen(){
  const [themes,setThemes]=useState<Theme[]>([]);
  const [presets,setPresets]=useState<PresetsResponse>({});
  const [loading,setLoading]=useState(true);
  const [busy,setBusy]=useState<string|null>(null);

  const load=useCallback(async()=>{
    try{
      setLoading(true);
      const [themeRes,presetRes]=await Promise.all([
        djangoApi<{results?:Theme[]}>("/api/themes/"),
        djangoApi<PresetsResponse>("/api/themes/presets/")
      ]);
      setThemes(themeRes.results??[]);
      setPresets(presetRes??{});
    }catch(e){
      Alert.alert("تعذر تحميل مكتبة التصاميم",e instanceof Error?e.message:"حاول مرة أخرى.");
    }finally{setLoading(false)}
  },[]);

  useEffect(()=>{void load()},[load]);

  const saved=useMemo(()=>themes.filter(t=>t.is_global),[themes]);

  async function installAndActivate(key:string){
    const preset=presets[key];
    if(!preset)return;
    setBusy(`use:${key}`);
    try{
      const created=await djangoApi<Theme>("/api/themes/install_preset/",{method:"POST",body:JSON.stringify({preset:key,name:preset.name})});
      await djangoApi(`/api/themes/${created.id}/activate/`,{method:"POST"});
      await load();
      router.push(`/admin/theme-builder?theme=${created.id}` as never);
    }catch(e){
      Alert.alert("تعذر تفعيل التصميم",e instanceof Error?e.message:"حاول مرة أخرى.");
    }finally{setBusy(null)}
  }

  async function activate(theme:Theme){
    setBusy(`a:${theme.id}`);
    try{ await djangoApi(`/api/themes/${theme.id}/activate/`,{method:"POST"}); await load(); }
    catch(e){Alert.alert("تعذر التفعيل",e instanceof Error?e.message:"حاول مرة أخرى.")}finally{setBusy(null)}
  }

  async function duplicate(theme:Theme){
    setBusy(`d:${theme.id}`);
    try{const copy=await djangoApi<Theme>(`/api/themes/${theme.id}/duplicate/`,{method:"POST",body:JSON.stringify({name:`نسخة — ${theme.name}`})});setThemes(x=>[copy,...x]);router.push(`/admin/theme-builder?theme=${copy.id}` as never)}
    catch(e){Alert.alert("تعذر النسخ",e instanceof Error?e.message:"حاول مرة أخرى.")}finally{setBusy(null)}
  }

  return <AdminLayout title="مكتبة تصاميم المتجر"><ScrollView style={{flex:1}} contentContainerStyle={styles.page} refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor={Colors.primary} />}>
    <View style={styles.hero}><View style={styles.heroIcon}><MaterialIcons name="web-asset" size={25} color="#FFF"/></View><View style={styles.heroCopy}><Text style={styles.heroTitle}>مكتبة التصاميم</Text><Text style={styles.heroText}>اختر أحد القالبين المرجعيين، أو افتح المصمم المتقدم للتحكم في كل جزء من الواجهة.</Text></View><TouchableOpacity style={styles.builderButton} onPress={()=>router.push("/admin/theme-builder" as never)}><MaterialIcons name="dashboard-customize" size={17} color="#FFF"/><Text style={styles.builderText}>المصمم المتقدم</Text></TouchableOpacity></View>
    <View style={styles.sectionHead}><View><Text style={styles.title}>القالبان المرجعيان</Text><Text style={styles.sub}>القوالب الأساسية محفوظة، وما تعدله يكون في نسخة مستقلة.</Text></View></View>
    {loading && Object.keys(presets).length===0?<ActivityIndicator color={Colors.primary} style={{marginVertical:30}}/>:<View style={styles.grid}>{(Object.keys(PRESET_META) as Array<keyof typeof PRESET_META>).map(key=>{const meta=PRESET_META[key];const preset=presets[key];const active=saved.some(t=>t.is_active&&t.layout?.family===key);return <View key={key} style={[styles.template,{backgroundColor:meta.bg,borderColor:`${meta.accent}25`}]}><View style={styles.previewHeader}><View style={[styles.logo,{backgroundColor:meta.accent}]}/><View style={[styles.search,{borderColor:`${meta.accent}35`}]}/><View style={styles.dot}/><View style={styles.dot}/></View><View style={[styles.previewHero,{backgroundColor:meta.accent}]}><View style={styles.heroLines}><View style={styles.l1}/><View style={styles.l2}/><View style={styles.cta}/></View><View style={styles.photo}/></View><View style={styles.previewSections}><View style={styles.pillRow}>{[1,2,3,4,5].map(i=><View key={i} style={[styles.pill,{borderColor:`${meta.accent}30`}]}/>)}</View><View style={styles.cardsRow}>{[1,2,3].map(i=><View key={i} style={styles.miniCard}/>)}</View></View><Text style={styles.templateTitle}>{meta.title}</Text><Text style={styles.templateSub}>{preset?.description??meta.subtitle}</Text><View style={styles.metaRow}><Text style={styles.metaText}>{preset?.sections?.length??0} أقسام أساسية</Text><Text style={styles.metaText}>{active?"مفعّل":"جاهز"}</Text></View><View style={styles.buttons}><TouchableOpacity disabled={!preset||!!busy} style={[styles.primaryButton,{backgroundColor:meta.accent}]} onPress={()=>installAndActivate(key)}>{busy===`use:${key}`?<ActivityIndicator color="#FFF"/>:<><MaterialIcons name="tune" size={17} color="#FFF"/><Text style={styles.primaryText}>استخدام وفتح المصمم</Text></>}</TouchableOpacity>{active?<View style={styles.activeBadge}><MaterialIcons name="check-circle" size={17} color={Colors.success}/><Text style={styles.activeText}>التصميم النشط</Text></View>:null}</View></View>})}</View>}
    <View style={styles.savedCard}><View style={styles.sectionHead}><View><Text style={styles.title}>التصاميم المحفوظة</Text><Text style={styles.sub}>افتح أي تصميم لتعديل الألوان، الأبعاد، الأقسام والبانرات.</Text></View></View>{saved.length===0?<Text style={styles.empty}>لم يتم إنشاء تصاميم مخصصة بعد.</Text>:saved.map(theme=><View key={theme.id} style={styles.savedRow}><View style={[styles.swatch,{backgroundColor:String(theme.tokens?.primary??Colors.primary)}]}><MaterialIcons name="palette" size={17} color="#FFF"/></View><View style={styles.savedCopy}><Text style={styles.savedName}>{theme.name}</Text><Text style={styles.savedMeta}>{theme.layout?.family??"custom"} · {theme.is_active?"نشط":"غير نشط"}</Text></View><TouchableOpacity disabled={!!busy||theme.is_active} style={styles.actionButton} onPress={()=>activate(theme)}><Text style={styles.actionText}>{theme.is_active?"نشط":"تفعيل"}</Text></TouchableOpacity><TouchableOpacity disabled={!!busy} style={styles.actionButton} onPress={()=>duplicate(theme)}><Text style={styles.actionText}>تعديل</Text></TouchableOpacity></View>)}</View>
  </ScrollView></AdminLayout>
}

const styles=StyleSheet.create({page:{padding:Spacing.md,paddingBottom:100},hero:{backgroundColor:"#101828",borderRadius:22,padding:18,flexDirection:"row-reverse",alignItems:"center",gap:12,marginBottom:16,...Shadow.md},heroIcon:{width:48,height:48,borderRadius:15,backgroundColor:Colors.primary,alignItems:"center",justifyContent:"center"},heroCopy:{flex:1,alignItems:"flex-end"},heroTitle:{color:"#FFF",fontSize:20,fontWeight:"900",textAlign:"right"},heroText:{color:"#C7CFD9",fontSize:10,lineHeight:18,textAlign:"right",marginTop:4},builderButton:{height:38,paddingHorizontal:11,borderRadius:10,backgroundColor:Colors.primary,flexDirection:"row-reverse",alignItems:"center",justifyContent:"center",gap:5},builderText:{color:"#FFF",fontSize:9,fontWeight:"900"},sectionHead:{flexDirection:"row-reverse",justifyContent:"space-between",alignItems:"center",marginBottom:10},title:{color:Colors.text,...Font.sectionTitle,textAlign:"right"},sub:{color:Colors.textSecondary,...Font.small,textAlign:"right",marginTop:2},grid:{flexDirection:"row-reverse",flexWrap:"wrap",gap:12},template:{flexGrow:1,flexBasis:340,minWidth:290,borderWidth:1,borderRadius:20,padding:12,...Shadow.sm},previewHeader:{height:34,borderRadius:9,backgroundColor:"#FFF",flexDirection:"row-reverse",alignItems:"center",gap:5,paddingHorizontal:7},logo:{width:22,height:22,borderRadius:7},search:{flex:1,height:18,borderWidth:1,borderRadius:99},dot:{width:17,height:17,borderRadius:99,backgroundColor:"#E5E7EB"},previewHero:{height:122,borderRadius:11,marginTop:7,padding:8,flexDirection:"row-reverse",justifyContent:"space-between",alignItems:"center"},heroLines:{width:"45%",alignItems:"flex-end",gap:6},l1:{height:9,width:"85%",borderRadius:7,backgroundColor:"#FFF"},l2:{height:6,width:"60%",borderRadius:7,backgroundColor:"#FFFFFFAA"},cta:{height:20,width:52,borderRadius:7,marginTop:3,backgroundColor:"#FFF"},photo:{width:"47%",height:"90%",borderRadius:10,backgroundColor:"#FFFFFF30"},previewSections:{marginTop:7},pillRow:{flexDirection:"row-reverse",gap:4},pill:{height:18,width:42,borderRadius:99,borderWidth:1,backgroundColor:"#FFF"},cardsRow:{flexDirection:"row-reverse",gap:5,marginTop:7},miniCard:{flex:1,height:52,borderRadius:8,backgroundColor:"#FFF",borderWidth:1,borderColor:"#E5E7EB"},templateTitle:{marginTop:10,fontSize:14,fontWeight:"900",color:Colors.text,textAlign:"right"},templateSub:{marginTop:3,fontSize:9,color:Colors.textSecondary,textAlign:"right",lineHeight:16},metaRow:{flexDirection:"row-reverse",justifyContent:"space-between",marginTop:8},metaText:{fontSize:8,color:Colors.textSecondary},buttons:{marginTop:10,gap:7},primaryButton:{height:42,borderRadius:12,flexDirection:"row-reverse",alignItems:"center",justifyContent:"center",gap:6},primaryText:{color:"#FFF",fontSize:10,fontWeight:"900"},activeBadge:{height:34,borderRadius:10,backgroundColor:Colors.successLight,flexDirection:"row-reverse",alignItems:"center",justifyContent:"center",gap:5},activeText:{color:Colors.success,fontSize:9,fontWeight:"900"},savedCard:{marginTop:14,backgroundColor:Colors.surface,borderWidth:1,borderColor:Colors.divider,borderRadius:18,padding:13,...Shadow.sm},empty:{paddingVertical:24,color:Colors.textSecondary,textAlign:"right",fontSize:10},savedRow:{minHeight:54,borderTopWidth:1,borderTopColor:Colors.divider,flexDirection:"row-reverse",alignItems:"center",gap:9},swatch:{width:36,height:36,borderRadius:11,alignItems:"center",justifyContent:"center"},savedCopy:{flex:1,alignItems:"flex-end"},savedName:{fontSize:11,fontWeight:"900",color:Colors.text},savedMeta:{fontSize:8,color:Colors.textSecondary,marginTop:2},actionButton:{height:33,paddingHorizontal:9,borderRadius:9,backgroundColor:Colors.surfaceAlt,justifyContent:"center",alignItems:"center",marginVertical:5},actionText:{fontSize:8,fontWeight:"900",color:Colors.text}});
