import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ActivityIndicator, FlatList, RefreshControl, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { ScreenContainer } from "@/components/screen-container";
import { djangoApi } from "@/lib/django-api";

type Chat = { id: number; vendor_name: string; order_number: string; subject: string; is_closed: boolean; updated_at: string; messages: { body: string; created_at: string; sender: number }[] };

export default function VendorMessagesScreen() {
  const [items, setItems] = useState<Chat[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const load = useCallback(async () => {
    try {
      const data = await djangoApi<{ results?: Chat[] }>("/api/order-chats/");
      setItems(data.results ?? []);
    } finally { setLoading(false); setRefreshing(false); }
  }, []);
  useEffect(() => { load(); }, [load]);
  return <ScreenContainer className="bg-[#F7F8FA]" edges={["top","bottom","left","right"]}>
    <View style={styles.header}><TouchableOpacity onPress={() => router.back()}><MaterialIcons name="arrow-forward" size={23} color="#111" /></TouchableOpacity><Text style={styles.title}>محادثات العملاء</Text><View style={{width:23}} /></View>
    {loading ? <View style={styles.center}><ActivityIndicator color="#E60023"/><Text style={styles.muted}>جارٍ تحميل المحادثات...</Text></View> : <FlatList data={items} keyExtractor={x=>String(x.id)} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={()=>{setRefreshing(true);load();}}/>} contentContainerStyle={styles.list} ListEmptyComponent={<View style={styles.empty}><MaterialIcons name="chat-bubble-outline" size={44} color="#D0D0D0"/><Text style={styles.emptyTitle}>لا توجد محادثات بعد</Text><Text style={styles.muted}>ستظهر هنا محادثة مستقلة لكل طلب وتاجر.</Text></View>} renderItem={({item})=><TouchableOpacity style={styles.card} onPress={()=>router.push(`/vendor/messages/${item.id}` as never)}><View style={styles.icon}><MaterialIcons name="chat" size={20} color="#FFF"/></View><View style={styles.copy}><View style={styles.row}><Text style={styles.order}>{item.order_number}</Text><Text style={styles.date}>{new Date(item.updated_at).toLocaleDateString("ar-YE")}</Text></View><Text style={styles.subject}>{item.subject || "محادثة الطلب"}</Text><Text numberOfLines={1} style={styles.preview}>{item.messages?.[item.messages.length-1]?.body || "بدء محادثة مع العميل"}</Text></View></TouchableOpacity>}/>} 
  </ScreenContainer>;
}
const styles=StyleSheet.create({header:{height:58,backgroundColor:"#FFF",paddingHorizontal:16,flexDirection:"row",alignItems:"center",justifyContent:"space-between",borderBottomWidth:1,borderColor:"#EEE"},title:{fontSize:17,fontWeight:"900",color:"#111"},list:{padding:12,paddingBottom:140},card:{backgroundColor:"#FFF",borderRadius:14,padding:13,marginBottom:9,flexDirection:"row-reverse",alignItems:"center",gap:12,borderWidth:1,borderColor:"#EEE"},icon:{width:42,height:42,borderRadius:13,backgroundColor:"#111",alignItems:"center",justifyContent:"center"},copy:{flex:1,alignItems:"flex-end"},row:{width:"100%",flexDirection:"row-reverse",justifyContent:"space-between"},order:{fontSize:13,fontWeight:"900",color:"#111"},date:{fontSize:10,color:"#999"},subject:{fontSize:12,fontWeight:"800",color:"#333",marginTop:5},preview:{fontSize:11,color:"#888",marginTop:4,width:"100%",textAlign:"right"},center:{flex:1,alignItems:"center",justifyContent:"center",gap:10},muted:{fontSize:12,color:"#888",textAlign:"center"},empty:{padding:50,alignItems:"center",gap:9},emptyTitle:{fontSize:15,fontWeight:"900",color:"#444"}});
