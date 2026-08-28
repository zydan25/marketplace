import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ActivityIndicator, Alert, Image, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useState } from "react";

import { ScreenContainer } from "@/components/screen-container";
import { useAuth } from "@/hooks/use-auth";
import { getOrder, updatePendingOrder, confirmReceived, rejectOrderItem, adminReleaseOrder, resolveItemDispute, updateOrderStatus, type StoreOrder } from "@/lib/order-api";

export default function OrderDetailsScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user, isAuthenticated } = useAuth();
  const [order, setOrder] = useState<StoreOrder | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [quantities, setQuantities] = useState<Record<number, number>>({});
  const [reason, setReason] = useState("");
  const [rejecting, setRejecting] = useState<number | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      setLoading(true);
      const value = await getOrder(Number(id));
      setOrder(value);
      setQuantities(value.items.reduce<Record<number, number>>((result, item) => {
        result[item.id] = item.quantity;
        return result;
      }, {}));
    } catch (error) {
      Alert.alert("تعذر فتح الطلب", error instanceof Error ? error.message : "حاول مجددًا.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (isAuthenticated) load();
  }, [isAuthenticated, load]);

  if (!isAuthenticated) return <ScreenContainer><View style={s.center}><Text>سجّل الدخول لعرض الطلب.</Text></View></ScreenContainer>;
  if (loading || !order) return <ScreenContainer><View style={s.center}><ActivityIndicator color="#E60023"/><Text style={s.muted}>جارٍ تحميل تفاصيل الطلب...</Text></View></ScreenContainer>;

  const isCustomer = user?.role === "customer";
  const admin = user?.role === "admin";
  const pending = order.status === "pending";
  const escrow = order.escrow;
  const disputedItems = new Set(
    Object.entries(escrow?.disputes ?? {})
      .filter(([, value]) => value.status === "pending")
      .map(([key]) => Number(key)),
  );

  async function saveEdit() {
    try {
      setSaving(true);
      const updated = await updatePendingOrder(order.id, {
        items: order.items.map((item) => ({ order_item_id: item.id, quantity: Math.max(1, quantities[item.id] ?? item.quantity) })),
      });
      setOrder(updated);
      setEditing(false);
      Alert.alert("تم تحديث الطلب", "تم تعديل الكميات وتحديث المبلغ المحجوز في الرصيد.");
    } catch (error) {
      Alert.alert("تعذر تعديل الطلب", error instanceof Error ? error.message : "تحقق من الرصيد والمخزون.");
    } finally {
      setSaving(false);
    }
  }

  function confirm() {
    Alert.alert(
      "تأكيد استلام نهائي",
      "هل استلمت طلبك حسب المواصفات المطلوبة وفحصت جميع القطع؟ بعد التأكيد لا يمكن التراجع عن هذه الخطوة، وسيبدأ إطلاق المستحقات وفق سياسة المنصة.",
      [
        { text: "مراجعة", style: "cancel" },
        {
          text: "نعم، استلمت وفحصت",
          style: "destructive",
          onPress: async () => {
            try {
              setSaving(true);
              await confirmReceived(order.id);
              await load();
            } catch (error) {
              Alert.alert("تعذر التأكيد", error instanceof Error ? error.message : "حاول مجددًا.");
            } finally {
              setSaving(false);
            }
          },
        },
      ],
    );
  }

  async function rejectItem(itemId: number) {
    if (!reason.trim()) return Alert.alert("سبب الاعتراض مطلوب", "اكتب سبب عدم مطابقة القطعة.");
    try {
      setSaving(true);
      await rejectOrderItem(order.id, itemId, reason.trim());
      setReason("");
      setRejecting(null);
      await load();
      Alert.alert("تم تسجيل الاعتراض", "بقي مبلغ هذه القطعة معلقًا حتى تتم المراجعة والحل.");
    } catch (error) {
      Alert.alert("تعذر تسجيل الاعتراض", error instanceof Error ? error.message : "حاول مجددًا.");
    } finally {
      setSaving(false);
    }
  }

  async function release() {
    try {
      setSaving(true);
      await adminReleaseOrder(order.id);
      await load();
      Alert.alert("تم إطلاق المستحقات", "تم تحويل المستحقات غير المتنازع عليها إلى محافظ التجار.");
    } catch (error) {
      Alert.alert("تعذر إطلاق المستحقات", error instanceof Error ? error.message : "تحقق من حالة الطلب.");
    } finally {
      setSaving(false);
    }
  }

  async function resolve(itemId: number, decision: "refund" | "release") {
    try {
      setSaving(true);
      await resolveItemDispute(order.id, itemId, decision);
      await load();
    } catch (error) {
      Alert.alert("تعذر حل الاعتراض", error instanceof Error ? error.message : "حاول مجددًا.");
    } finally {
      setSaving(false);
    }
  }

  async function status(next: "confirmed" | "processing" | "shipped" | "delivered" | "cancelled") {
    try {
      setSaving(true);
      await updateOrderStatus(order.id, next);
      await load();
    } catch (error) {
      Alert.alert("تعذر تغيير الحالة", error instanceof Error ? error.message : "حاول مجددًا.");
    } finally {
      setSaving(false);
    }
  }

  return <ScreenContainer className="bg-[#F6F6F6]" edges={["top", "bottom", "left", "right"]}>
    <View style={s.header}><TouchableOpacity onPress={() => router.back()}><MaterialIcons name="arrow-forward" size={24} color="#111" /></TouchableOpacity><View style={s.headerCopy}><Text style={s.title}>تفاصيل الطلب</Text><Text style={s.code}>{order.orderCode} · {order.statusLabel}</Text></View><TouchableOpacity onPress={() => router.push(`/order-chat/${order.id}` as never)}><MaterialIcons name="chat" size={22} color="#111" /></TouchableOpacity></View>
    <ScrollView contentContainerStyle={s.page}>
      <View style={s.timeline}><Text style={s.sectionTitle}>حالة الطلب</Text>{(order.timeline ?? []).length ? order.timeline!.map((event, index) => <View key={`${event.createdAt}-${index}`} style={s.timelineRow}><View style={s.dot}/><View style={s.timelineCopy}><Text style={s.timelineTitle}>{label(event.status)}</Text><Text style={s.timelineTime}>{new Date(event.createdAt).toLocaleString("ar-YE")}</Text>{event.note ? <Text style={s.timelineNote}>{event.note}</Text> : null}</View></View>) : <View style={s.currentStatus}><Text style={s.currentStatusText}>{order.statusLabel}</Text></View>}</View>
      <View style={s.card}><View style={s.cardHeader}><Text style={s.sectionTitle}>المنتجات ({order.items.length})</Text>{pending && isCustomer && !editing ? <TouchableOpacity onPress={() => setEditing(true)}><Text style={s.link}>تعديل الطلب</Text></TouchableOpacity> : editing ? <TouchableOpacity onPress={saveEdit} disabled={saving}><Text style={s.link}>حفظ</Text></TouchableOpacity> : null}</View>{order.items.map(item => <View key={item.id} style={s.item}><TouchableOpacity style={s.imageBox} onPress={() => router.push(`/product/${item.productId}` as never)}>{item.imageUrl ? <Image source={{uri:item.imageUrl}} style={s.image}/> : <MaterialIcons name="image" size={24} color="#AAA"/>}</TouchableOpacity><View style={s.itemCopy}><TouchableOpacity onPress={() => router.push(`/product/${item.productId}` as never)}><Text style={s.itemName}>{item.productName}</Text></TouchableOpacity><Text style={s.meta}>اللون: {item.color || "غير محدد"} · المقاس: {item.size || "غير محدد"}</Text><Text style={s.meta}>SKU: {item.sku}</Text>{editing ? <View style={s.qty}><TouchableOpacity onPress={() => setQuantities(q => ({...q,[item.id]:Math.max(1,(q[item.id]??item.quantity)-1)}))}><MaterialIcons name="remove" size={18}/></TouchableOpacity><Text style={s.qtyText}>{quantities[item.id] ?? item.quantity}</Text><TouchableOpacity onPress={() => setQuantities(q => ({...q,[item.id]:(q[item.id]??item.quantity)+1}))}><MaterialIcons name="add" size={18}/></TouchableOpacity></View> : <Text style={s.qtyText}>الكمية: {item.quantity}</Text>}</View><View style={s.itemRight}><Text style={s.itemPrice}>{(item.unitPrice*item.quantity).toLocaleString("ar-YE")} {order.currency}</Text>{isCustomer && order.status === "delivered" && escrow && !escrow.customer_confirmed ? <TouchableOpacity onPress={() => setRejecting(rejecting === item.id ? null : item.id)} style={s.rejectButton}><Text style={s.rejectText}>اعتراض</Text></TouchableOpacity> : null}{disputedItems.has(item.id) ? <Text style={s.dispute}>اعتراض معلّق</Text> : null}</View></View>)}
      {rejecting !== null ? <View style={s.reasonBox}><Text style={s.reasonTitle}>سبب الاعتراض على القطعة</Text><TextInput value={reason} onChangeText={setReason} style={s.reasonInput} placeholder="اذكر ما لا يطابق الطلب" placeholderTextColor="#999" multiline textAlign="right"/><View style={s.reasonActions}><TouchableOpacity onPress={() => setRejecting(null)} style={s.cancelButton}><Text>إلغاء</Text></TouchableOpacity><TouchableOpacity onPress={() => rejectItem(rejecting)} disabled={saving} style={s.dangerButton}><Text style={s.dangerText}>إرسال الاعتراض</Text></TouchableOpacity></View></View> : null}</View>
      <View style={s.card}><Text style={s.sectionTitle}>العنوان والتوصيل</Text><Text style={s.address}>{String(order.shippingAddress?.title ?? "")}</Text><Text style={s.address}>{String(order.shippingAddress?.district ?? "")} · {String(order.shippingAddress?.street ?? "")}</Text><View style={s.moneyRow}><Text style={s.moneyLabel}>رسوم التوصيل</Text><Text style={s.moneyValue}>{order.shippingFee.toLocaleString("ar-YE")} {order.currency}</Text></View></View>
      <View style={s.card}><Text style={s.sectionTitle}>الملخص المالي</Text><Row label="المجموع الفرعي" value={order.subtotal}/><Row label="الخصم" value={-order.discount}/><Row label="الشحن" value={order.shippingFee}/><View style={s.divider}/><Row label="الإجمالي" value={order.totalAmount} strong/><View style={s.holdBox}>{escrow ? <><MaterialIcons name="lock-clock" size={20} color="#A96A00"/><Text style={s.holdText}>المبلغ المحجوز: {escrow.held_amount} {order.currency} · المتاح للتاجر لا يطلق حتى انتهاء المراجعة.</Text></> : <Text style={s.meta}>حالة الدفع: {order.paymentStatus}</Text>}</View></View>
      {isCustomer && order.status === "delivered" && escrow && !escrow.customer_confirmed ? <TouchableOpacity disabled={saving} style={s.confirmButton} onPress={confirm}><MaterialIcons name="verified" size={20} color="#FFF"/><Text style={s.confirmText}>تأكيد الاستلام النهائي</Text></TouchableOpacity> : null}
      {admin && escrow && escrow.customer_confirmed ? <TouchableOpacity disabled={saving} style={s.releaseButton} onPress={release}><MaterialIcons name="account-balance-wallet" size={20} color="#FFF"/><Text style={s.confirmText}>إطلاق المستحقات غير المتنازع عليها</Text></TouchableOpacity> : null}
      {admin && Object.entries(escrow?.disputes ?? {}).filter(([, dispute]) => dispute.status === "pending").map(([key, dispute]) => <View key={key} style={s.adminDispute}><Text style={s.sectionTitle}>اعتراض القطعة #{key}</Text><Text style={s.meta}>{dispute.reason}</Text><View style={s.reasonActions}><TouchableOpacity disabled={saving} onPress={() => resolve(Number(key), "refund")} style={s.dangerButton}><Text style={s.dangerText}>استرداد للعميل</Text></TouchableOpacity><TouchableOpacity disabled={saving} onPress={() => resolve(Number(key), "release")} style={s.okButton}><Text style={s.okText}>إطلاق للتاجر</Text></TouchableOpacity></View></View>)}
      {admin ? <View style={s.card}><Text style={s.sectionTitle}>إدارة الحالة</Text><View style={s.actionWrap}>{(["confirmed","processing","shipped","delivered","cancelled"] as const).map(next => <TouchableOpacity key={next} disabled={saving} onPress={() => status(next)} style={s.statusButton}><Text style={s.statusButtonText}>{label(next)}</Text></TouchableOpacity>)}</View></View> : null}
    </ScrollView>
  </ScreenContainer>;
}

function Row({ label, value, strong = false }: { label: string; value: number; strong?: boolean }) {
  return <View style={s.moneyRow}><Text style={[s.moneyValue, strong && s.totalValue]}>{value.toLocaleString("ar-YE")} {"ر.ي"}</Text><Text style={[s.moneyLabel, strong && s.totalLabel]}>{label}</Text></View>;
}

function label(value: string) { return ({ pending: "قيد الانتظار", confirmed: "مؤكد", processing: "قيد التجهيز", shipped: "تم الشحن", delivered: "تم التسليم", cancelled: "ملغي", refunded: "مسترد" } as Record<string, string>)[value] || value; }

const s = StyleSheet.create({ header:{height:58,backgroundColor:"#FFF",paddingHorizontal:15,flexDirection:"row",alignItems:"center",justifyContent:"space-between",borderBottomWidth:1,borderColor:"#E7E7E7"},headerCopy:{alignItems:"center"},title:{fontSize:15,fontWeight:"900",color:"#111"},code:{fontSize:9,color:"#777",marginTop:2},page:{padding:12,paddingBottom:100},card:{backgroundColor:"#FFF",borderRadius:13,padding:14,marginBottom:10},cardHeader:{flexDirection:"row-reverse",justifyContent:"space-between",alignItems:"center",marginBottom:7},sectionTitle:{fontSize:14,fontWeight:"900",color:"#111"},link:{color:"#E60023",fontSize:11,fontWeight:"900"},item:{flexDirection:"row-reverse",alignItems:"center",gap:9,paddingVertical:9,borderTopWidth:1,borderColor:"#F2F2F2"},imageBox:{width:58,height:68,borderRadius:8,backgroundColor:"#F3F3F3",alignItems:"center",justifyContent:"center",overflow:"hidden"},image:{width:"100%",height:"100%"},itemCopy:{flex:1,alignItems:"flex-end"},itemName:{fontSize:12,fontWeight:"900",color:"#222",textAlign:"right"},meta:{fontSize:9,color:"#777",marginTop:3,textAlign:"right"},itemRight:{alignItems:"flex-start",minWidth:78},itemPrice:{fontSize:10,fontWeight:"900",color:"#111"},qty:{flexDirection:"row-reverse",gap:12,alignItems:"center",borderWidth:1,borderColor:"#E5E5E5",borderRadius:18,paddingHorizontal:8,paddingVertical:4,marginTop:6},qtyText:{fontSize:10,fontWeight:"900",color:"#333"},rejectButton:{marginTop:5,paddingHorizontal:8,paddingVertical:5,borderRadius:9,backgroundColor:"#FFF1F2"},rejectText:{fontSize:8,fontWeight:"900",color:"#B4232A"},dispute:{fontSize:8,color:"#A96A00",fontWeight:"800",marginTop:4},reasonBox:{marginTop:8,padding:10,borderRadius:9,backgroundColor:"#FFF8E8",borderWidth:1,borderColor:"#F0DEAD"},reasonTitle:{fontSize:11,fontWeight:"900",textAlign:"right"},reasonInput:{minHeight:70,backgroundColor:"#FFF",marginTop:7,padding:9,borderRadius:8,borderWidth:1,borderColor:"#E4E4E4",textAlignVertical:"top"},reasonActions:{flexDirection:"row-reverse",gap:8,justifyContent:"flex-start",marginTop:8},cancelButton:{paddingHorizontal:12,paddingVertical:8,borderWidth:1,borderColor:"#DDD",borderRadius:8},dangerButton:{backgroundColor:"#D72638",paddingHorizontal:12,paddingVertical:8,borderRadius:8},dangerText:{color:"#FFF",fontSize:10,fontWeight:"900"},okButton:{backgroundColor:"#168451",paddingHorizontal:12,paddingVertical:8,borderRadius:8},okText:{color:"#FFF",fontSize:10,fontWeight:"900"},address:{fontSize:11,color:"#555",textAlign:"right",marginTop:5},moneyRow:{flexDirection:"row-reverse",justifyContent:"space-between",paddingVertical:5},moneyLabel:{fontSize:11,color:"#666"},moneyValue:{fontSize:12,fontWeight:"800",color:"#333"},divider:{height:1,backgroundColor:"#EEE",marginVertical:6},totalValue:{fontSize:18,color:"#E60023",fontWeight:"900"},totalLabel:{fontSize:13,color:"#111",fontWeight:"900"},holdBox:{flexDirection:"row-reverse",gap:8,alignItems:"flex-start",backgroundColor:"#FFF8E8",padding:10,borderRadius:9,marginTop:8},holdText:{flex:1,color:"#8B6200",fontSize:10,lineHeight:16,textAlign:"right"},confirmButton:{height:50,borderRadius:25,backgroundColor:"#168451",flexDirection:"row-reverse",gap:8,alignItems:"center",justifyContent:"center",marginBottom:10},releaseButton:{height:50,borderRadius:25,backgroundColor:"#111",flexDirection:"row-reverse",gap:8,alignItems:"center",justifyContent:"center",marginBottom:10},confirmText:{color:"#FFF",fontSize:13,fontWeight:"900"},adminDispute:{backgroundColor:"#FFF8E8",borderWidth:1,borderColor:"#F0DEAD",padding:12,borderRadius:11,marginBottom:10},actionWrap:{flexDirection:"row-reverse",flexWrap:"wrap",gap:7,marginTop:8},statusButton:{paddingHorizontal:10,paddingVertical:8,borderRadius:9,backgroundColor:"#F3F3F3",borderWidth:1,borderColor:"#E2E2E2"},statusButtonText:{fontSize:9,fontWeight:"800",color:"#222"},timeline:{backgroundColor:"#FFF",borderRadius:13,padding:14,marginBottom:10},timelineRow:{flexDirection:"row-reverse",gap:9,paddingVertical:5},dot:{width:9,height:9,borderRadius:5,backgroundColor:"#168451",marginTop:4},timelineCopy:{flex:1,alignItems:"flex-end"},timelineTitle:{fontSize:11,fontWeight:"900",color:"#222"},timelineTime:{fontSize:8,color:"#999",marginTop:2},timelineNote:{fontSize:9,color:"#777",marginTop:2},currentStatus:{backgroundColor:"#F4F4F4",padding:10,borderRadius:9},currentStatusText:{fontSize:12,fontWeight:"900",textAlign:"center"},center:{flex:1,alignItems:"center",justifyContent:"center",padding:28,gap:10},muted:{fontSize:12,color:"#777"} });