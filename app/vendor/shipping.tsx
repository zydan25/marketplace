import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Alert, FlatList, StyleSheet, Switch, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";

import { ScreenContainer } from "@/components/screen-container";
import { djangoApi } from "@/lib/django-api";

type City = { id: number; name: string };
type Fee = { id: number; city: number; city_name: string; fee: string; is_active: boolean };

export default function VendorShippingScreen() {
  const [cities, setCities] = useState<City[]>([]);
  const [fees, setFees] = useState<Record<number, Fee>>({});
  const [values, setValues] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<number | null>(null);
  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [cityRes, feeRes] = await Promise.all([djangoApi<{ results?: City[] }>("/api/cities/"), djangoApi<{ results?: Fee[] }>("/api/vendor-city-shipping/")]);
      setCities(cityRes.results ?? []);
      const map: Record<number, Fee> = {};
      const nextValues: Record<number, string> = {};
      (feeRes.results ?? []).forEach((fee) => { map[fee.city] = fee; nextValues[fee.city] = String(fee.fee); });
      setFees(map); setValues(nextValues);
    } catch (error) { Alert.alert("تعذر تحميل رسوم التوصيل", error instanceof Error ? error.message : "حاول مجددًا."); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);
  async function save(city: City) {
    const fee = Math.max(0, Number(values[city.id] ?? 0));
    try {
      setSaving(city.id);
      const existing = fees[city.id];
      const payload = { city: city.id, fee: fee.toFixed(2), is_active: true };
      const result = existing ? await djangoApi<Fee>(`/api/vendor-city-shipping/${existing.id}/`, { method: "PATCH", body: JSON.stringify(payload) }) : await djangoApi<Fee>("/api/vendor-city-shipping/", { method: "POST", body: JSON.stringify(payload) });
      setFees((current) => ({ ...current, [city.id]: result })); setValues((current) => ({ ...current, [city.id]: String(result.fee) }));
    } catch (error) { Alert.alert("تعذر حفظ الرسم", error instanceof Error ? error.message : "تحقق من السعر."); }
    finally { setSaving(null); }
  }
  async function toggle(city: City, active: boolean) {
    const fee = fees[city.id]; if (!fee) return;
    try { const result = await djangoApi<Fee>(`/api/vendor-city-shipping/${fee.id}/`, { method: "PATCH", body: JSON.stringify({ is_active: active }) }); setFees((current) => ({ ...current, [city.id]: result })); }
    catch (error) { Alert.alert("تعذر تحديث الحالة", error instanceof Error ? error.message : "حاول مجددًا."); }
  }
  if (loading) return <ScreenContainer><View style={styles.center}><ActivityIndicator color="#E60023"/></View></ScreenContainer>;
  return <ScreenContainer className="bg-[#F6F6F6]" edges={["top","bottom","left","right"]}><View style={styles.header}><TouchableOpacity onPress={() => router.back()}><MaterialIcons name="arrow-forward" size={24} color="#111"/></TouchableOpacity><View style={styles.headerCopy}><Text style={styles.title}>رسوم التوصيل</Text><Text style={styles.sub}>سعر مستقل لكل محافظة</Text></View><MaterialIcons name="local-shipping" size={23} color="#E60023"/></View><View style={styles.info}><MaterialIcons name="info-outline" size={20} color="#168451"/><Text style={styles.infoText}>يظهر رسم المحافظة للعميل في ملخص الطلب ويُحسب من الخادم عند إنشاء الطلب، وليس من التطبيق.</Text></View><FlatList data={cities} keyExtractor={(item)=>String(item.id)} contentContainerStyle={styles.list} renderItem={({item})=>{const fee=fees[item.id];return <View style={styles.card}><View style={styles.cityTop}><View style={styles.switchRow}>{fee?<Switch value={fee.is_active} onValueChange={(value)=>toggle(item,value)} trackColor={{true:"#168451"}}/>:null}<Text style={styles.activeText}>{fee?.is_active===false?"متوقف":"مفعل"}</Text></View><View style={styles.cityCopy}><Text style={styles.cityName}>{item.name}</Text><Text style={styles.cityMeta}>رسوم التوصيل للعميل</Text></View></View><View style={styles.editRow}><TextInput value={values[item.id] ?? "0"} onChangeText={(value)=>setValues((current)=>({...current,[item.id]:value.replace(/[^0-9.]/g,"")}))} keyboardType="decimal-pad" style={styles.input} textAlign="right" placeholder="0"/><Text style={styles.currency}>ر.ي</Text><TouchableOpacity style={styles.saveButton} disabled={saving===item.id} onPress={()=>save(item)}>{saving===item.id?<ActivityIndicator color="#FFF"/>:<Text style={styles.saveText}>حفظ</Text>}</TouchableOpacity></View></View>}} /></ScreenContainer>;
}
const styles=StyleSheet.create({header:{height:60,paddingHorizontal:16,backgroundColor:"#FFF",flexDirection:"row-reverse",alignItems:"center",justifyContent:"space-between",borderBottomWidth:1,borderColor:"#EEE"},headerCopy:{flex:1,alignItems:"flex-end",marginHorizontal:12},title:{fontSize:18,fontWeight:"900",color:"#111"},sub:{fontSize:9,color:"#888",marginTop:2},info:{margin:12,padding:12,borderRadius:11,backgroundColor:"#F2FAF5",borderWidth:1,borderColor:"#D9EFE0",flexDirection:"row-reverse",alignItems:"flex-start",gap:8},infoText:{flex:1,textAlign:"right",fontSize:10,color:"#54645A",lineHeight:17},list:{paddingHorizontal:12,paddingBottom:120},card:{backgroundColor:"#FFF",borderRadius:12,padding:12,marginBottom:8,borderWidth:1,borderColor:"#EEE"},cityTop:{flexDirection:"row-reverse",alignItems:"center",justifyContent:"space-between"},cityCopy:{flex:1,alignItems:"flex-end"},cityName:{fontSize:14,fontWeight:"900",color:"#111"},cityMeta:{fontSize:9,color:"#888",marginTop:2},switchRow:{flexDirection:"row-reverse",alignItems:"center",gap:4},activeText:{fontSize:8,color:"#777"},editRow:{flexDirection:"row-reverse",alignItems:"center",gap:8,marginTop:10},input:{height:42,flex:1,borderWidth:1,borderColor:"#E5E5E5",borderRadius:9,backgroundColor:"#FAFAFA",paddingHorizontal:10,color:"#111"},currency:{fontSize:10,color:"#777"},saveButton:{height:42,minWidth:68,borderRadius:9,backgroundColor:"#111",alignItems:"center",justifyContent:"center"},saveText:{color:"#FFF",fontSize:11,fontWeight:"900"},center:{flex:1,alignItems:"center",justifyContent:"center"}});
