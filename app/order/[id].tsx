import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ActivityIndicator, Alert, FlatList, KeyboardAvoidingView, Platform, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ScreenContainer } from "@/components/screen-container";
import { useAuth } from "@/hooks/use-auth";
import { formatYER } from "@/lib/catalog";
import { djangoApi } from "@/lib/django-api";
import { getOrder, type OrderChat, type StoreOrder } from "@/lib/order-api";

type ChatMessage = { id: number; sender: number; sender_name: string; body: string; attachment_url: string | null; is_read: boolean; created_at: string };

export default function OrderChatScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user, isAuthenticated } = useAuth();
  const [order, setOrder] = useState<StoreOrder | null>(null);
  const [chats, setChats] = useState<OrderChat[]>([]);
  const [selectedChatId, setSelectedChatId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [draft, setDraft] = useState("");

  const load = useCallback(async () => {
    if (!id) return;
    try {
      setLoading(true);
      const [nextOrder, nextChats] = await Promise.all([
        getOrder(Number(id)),
        djangoApi<OrderChat[] | { results?: OrderChat[] }>("/api/order-chats/ensure_for_order/", { method: "POST", body: JSON.stringify({ order_id: Number(id) }) }),
      ]);
      const normalizedChats = Array.isArray(nextChats) ? nextChats : (nextChats.results ?? []);
      setOrder(nextOrder);
      setChats(normalizedChats);
      setSelectedChatId((current) => current && normalizedChats.some((chat) => chat.id === current) ? current : normalizedChats[0]?.id ?? null);
    } catch (error) {
      Alert.alert("تعذر فتح المحادثة", error instanceof Error ? error.message : "حاول مرة أخرى.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { if (isAuthenticated) void load(); }, [isAuthenticated, load]);

  const selectedChat = useMemo(() => chats.find((chat) => chat.id === selectedChatId) ?? null, [chats, selectedChatId]);
  const messages = selectedChat?.messages ?? [];

  async function send() {
    const body = draft.trim();
    if (!selectedChat || !body) return;
    try {
      setSending(true);
      await djangoApi(`/api/order-chats/${selectedChat.id}/send_message/`, { method: "POST", body: JSON.stringify({ body }) });
      setDraft("");
      await load();
    } catch (error) {
      Alert.alert("تعذر إرسال الرسالة", error instanceof Error ? error.message : "حاول مرة أخرى.");
    } finally {
      setSending(false);
    }
  }

  if (!isAuthenticated) return <ScreenContainer edges={["top", "bottom", "left", "right"]} className="bg-white"><View style={s.center}><Text style={s.centerText}>سجّل الدخول للوصول إلى محادثة الطلب.</Text><TouchableOpacity style={s.darkButton} onPress={() => router.replace("/login" as never)}><Text style={s.darkButtonText}>تسجيل الدخول</Text></TouchableOpacity></View></ScreenContainer>;
  if (loading || !order) return <ScreenContainer edges={["top", "bottom", "left", "right"]} className="bg-white"><View style={s.center}><ActivityIndicator color="#E60023" /><Text style={s.centerText}>جارٍ تحميل الطلب والمحادثات...</Text></View></ScreenContainer>;

  return <ScreenContainer edges={["top", "bottom", "left", "right"]} className="bg-[#F6F6F6]"><View style={s.header}><TouchableOpacity onPress={() => router.back()} style={s.icon}><MaterialIcons name="arrow-forward" size={23} color="#171717" /></TouchableOpacity><View style={s.headerCopy}><Text style={s.headerTitle}>الطلب {order.orderCode}</Text><Text style={s.status}>{order.statusLabel}</Text></View><View style={{ width: 38 }} /></View><FlatList data={messages} keyExtractor={(item) => String(item.id)} refreshing={loading} onRefresh={load} contentContainerStyle={s.list} ListHeaderComponent={<><View style={s.chatPicker}>{chats.map((chat) => <TouchableOpacity key={chat.id} style={[s.chatChip, selectedChatId === chat.id && s.chatChipActive]} onPress={() => setSelectedChatId(chat.id)}><MaterialIcons name="storefront" size={15} color={selectedChatId === chat.id ? "#FFF" : "#555"} /><Text style={[s.chatChipText, selectedChatId === chat.id && s.chatChipTextActive]}>{chat.vendor_name}</Text></TouchableOpacity>)}</View><View style={s.orderCard}><Text style={s.orderTitle}>ملخص الطلب</Text>{order.items.map((line) => <View key={line.id} style={s.line}><View style={s.lineCopy}><Text style={s.lineName}>{line.quantity} × {line.productName}</Text><Text style={s.lineMeta}>{line.color || ""}{line.size ? ` · ${line.size}` : ""}</Text></View><Text style={s.linePrice}>{formatYER(line.unitPrice * line.quantity)}</Text></View>)}<View style={s.total}><Text style={s.totalLabel}>إجمالي الطلب</Text><Text style={s.totalValue}>{formatYER(order.totalAmount)}</Text></View></View></>} renderItem={({ item }) => <ChatBubble item={item} own={item.sender === user?.id} />} ListEmptyComponent={<View style={s.empty}><MaterialIcons name="forum" size={38} color="#AAA" /><Text style={s.centerText}>لا توجد رسائل بعد. ابدأ المحادثة مع التاجر.</Text></View>} /><KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} keyboardVerticalOffset={Platform.OS === "ios" ? 80 : 0}><View style={s.composer}><TextInput value={draft} onChangeText={setDraft} style={s.input} placeholder="اكتب رسالتك للتاجر" placeholderTextColor="#8C8C8C" textAlign="right" returnKeyType="send" onSubmitEditing={send} /><TouchableOpacity style={[s.sendButton, sending && s.disabled]} onPress={send} disabled={sending || !draft.trim()}><MaterialIcons name="send" size={19} color="#FFF" /></TouchableOpacity></View></KeyboardAvoidingView></ScreenContainer>;
}
function ChatBubble({ item, own }: { item: { sender: number; sender_name: string; body: string; attachment_url: string | null; created_at: string }; own: boolean }) { return <View style={[s.messageRow, own && s.ownRow]}><View style={[s.bubble, own ? s.ownBubble : s.otherBubble]}>{item.attachment_url ? <Text style={s.attachment}>مرفق: {item.attachment_url}</Text> : null}<Text style={[s.messageText, own && s.ownText]}>{item.body}</Text><Text style={[s.time, own && s.ownTime]}>{new Date(item.created_at).toLocaleTimeString("ar-YE", { hour: "2-digit", minute: "2-digit" })}</Text></View></View>; }
const s = StyleSheet.create({header:{height:58,backgroundColor:"#FFF",paddingHorizontal:15,flexDirection:"row-reverse",alignItems:"center",justifyContent:"space-between",borderBottomWidth:1,borderColor:"#E7E7E7"},icon:{width:38,height:38,alignItems:"center",justifyContent:"center"},headerCopy:{alignItems:"center"},headerTitle:{fontSize:14,fontWeight:"900",color:"#171717"},status:{fontSize:9,color:"#8A6500",marginTop:2},list:{padding:12,paddingBottom:20},chatPicker:{flexDirection:"row-reverse",gap:7,marginBottom:10,flexWrap:"wrap"},chatChip:{flexDirection:"row-reverse",alignItems:"center",gap:5,paddingHorizontal:10,paddingVertical:8,borderRadius:18,borderWidth:1,borderColor:"#DDD",backgroundColor:"#FFF"},chatChipActive:{backgroundColor:"#111",borderColor:"#111"},chatChipText:{fontSize:10,color:"#555",fontWeight:"800"},chatChipTextActive:{color:"#FFF"},orderCard:{backgroundColor:"#FFF",borderRadius:14,padding:13,marginBottom:12,borderWidth:1,borderColor:"#ECECEC"},orderTitle:{fontSize:14,fontWeight:"900",color:"#111",textAlign:"right",marginBottom:7},line:{flexDirection:"row-reverse",justifyContent:"space-between",gap:10,paddingVertical:8,borderTopWidth:1,borderColor:"#F1F1F1"},lineCopy:{flex:1,alignItems:"flex-end"},lineName:{fontSize:11,fontWeight:"800",color:"#222",textAlign:"right"},lineMeta:{fontSize:9,color:"#777",marginTop:3},linePrice:{fontSize:10,fontWeight:"900",color:"#E60023"},total:{flexDirection:"row-reverse",justifyContent:"space-between",borderTopWidth:1,borderColor:"#EAEAEA",paddingTop:9,marginTop:5},totalLabel:{fontSize:12,fontWeight:"900"},totalValue:{fontSize:15,fontWeight:"900",color:"#E60023"},messageRow:{alignItems:"flex-end",marginBottom:8},ownRow:{alignItems:"flex-start"},bubble:{maxWidth:"82%",padding:10,borderRadius:13},ownBubble:{backgroundColor:"#111"},otherBubble:{backgroundColor:"#FFF",borderWidth:1,borderColor:"#EEE"},messageText:{fontSize:12,color:"#333",lineHeight:18,textAlign:"right"},ownText:{color:"#FFF"},attachment:{fontSize:9,color:"#777",marginBottom:4},time:{fontSize:8,color:"#999",marginTop:4,textAlign:"right"},ownTime:{color:"#CFCFCF"},composer:{backgroundColor:"#FFF",borderTopWidth:1,borderColor:"#E6E6E6",padding:9,flexDirection:"row-reverse",gap:8,alignItems:"center"},input:{flex:1,height:43;backgroundColor:"#F2F2F2",borderRadius:22,paddingHorizontal:14,fontSize:12},sendButton:{width:43,height:43,borderRadius:22,backgroundColor:"#E60023",alignItems:"center",justifyContent:"center"},disabled:{opacity:.45},center:{flex:1,alignItems:"center",justifyContent:"center",padding:28,gap:12},centerText:{fontSize:12,color:"#666",textAlign:"center"},darkButton:{backgroundColor:"#111",paddingHorizontal:22,paddingVertical:12,borderRadius:22},darkButtonText:{color:"#FFF",fontWeight:"800"},empty:{alignItems:"center",paddingVertical:35}}
);