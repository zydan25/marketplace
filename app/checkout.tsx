import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { Alert, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useState } from "react";

import { formatYER } from "@/lib/catalog";
import { useCart } from "@/lib/cart-context";
import { ScreenContainer } from "@/components/screen-container";
import { createOrder } from "@/lib/order-api";
import { useEffect } from "react";

export default function CheckoutScreen() {
  const { items, removeItem } = useCart(); const { lines } = useLocalSearchParams<{ lines?: string }>(); const [submitting, setSubmitting] = useState(false); const selectedIds = new Set((lines ?? "").split(",").filter(Boolean)); const orderItems = selectedIds.size ? items.filter((item) => selectedIds.has(item.lineId)) : items; const subtotal = orderItems.reduce((total, item) => total + item.product.price * item.quantity, 0); const totalQuantity = orderItems.reduce((total, item) => total + item.quantity, 0);
  const [serverData, setServerData] = useState<any>(null);
  
  useEffect(() => {
    if (orderItems.length > 0 && useCart().validateCartWithServer) {
      useCart().validateCartWithServer?.()
        .then(setServerData)
        .catch(() => undefined);
    }
  }, []);

  const submit = async () => { 
    if (!orderItems.length) { Alert.alert("الحقيبة فارغة", "أضيفي منتجًا واحدًا على الأقل قبل إكمال الطلب."); return; } 
    try { 
      setSubmitting(true); 
      // Call validation first to ensure prices and stock are up to date
      const validation = await useCart().validateCartWithServer?.();
      if (!validation?.valid) {
        Alert.alert("تحديث في السلة", validation?.errors?.join("\n") || "تغيرت بعض المنتجات أو الأسعار.");
        setServerData(validation);
        return;
      }
      
      const order = await createOrder(orderItems.map((item) => ({ productId: Number(item.product.id), color: item.color, size: item.size, quantity: item.quantity }))); 
      orderItems.forEach((item) => removeItem(item.lineId)); 
      router.replace(`/order-chat/${order.id}` as never); 
    } catch (error) { 
      Alert.alert("تعذر إنشاء الطلب", error instanceof Error ? error.message : "سجّلي الدخول ثم حاولي مرة أخرى."); 
    } finally { 
      setSubmitting(false); 
    } 
  };
  return <ScreenContainer edges={["top", "bottom", "left", "right"]} className="bg-[#F6F6F6]"><View style={styles.header}><TouchableOpacity onPress={() => router.back()}><MaterialIcons name="close" size={24} color="#171717" /></TouchableOpacity><Text style={styles.headerTitle}>مراجعة الطلب</Text><View style={{ width: 24 }} /></View><ScrollView contentContainerStyle={styles.content}><View style={styles.card}><Text style={styles.cardTitle}>الأصناف المحددة ({totalQuantity})</Text>{orderItems.map((item) => <View key={item.lineId} style={styles.itemLine}><Text style={styles.lineValue}>{formatYER(item.product.price * item.quantity)}</Text><View style={styles.lineCopy}><Text style={styles.lineLabel}>{item.quantity} × {item.product.name}</Text><Text style={styles.variant}>{item.color} · {item.size}</Text></View></View>)}<View style={styles.divider} /><View style={styles.itemLine}><Text style={styles.total}>{serverData ? formatYER(serverData.total) : formatYER(subtotal)}</Text><Text style={styles.totalLabel}>الإجمالي النهائي</Text></View></View><View style={styles.card}><Text style={styles.cardTitle}>طريقة إتمام الطلب</Text><View style={styles.method}><MaterialIcons name="chat-bubble-outline" size={23} color="#E60023" /><View style={styles.methodCopy}><Text style={styles.methodTitle}>دردشة خاصة لطلبك</Text><Text style={styles.methodText}>بعد التأكيد ستفتح لك محادثة لإرسال إشعار الدفع ومتابعة الشحن مع الإدارة.</Text></View></View></View>
<View style={styles.card}><Text style={styles.cardTitle}>عنوان التوصيل</Text><TouchableOpacity style={styles.method} onPress={() => router.push("/addresses" as never)}><MaterialIcons name="location-on" size={23} color="#E60023" /><View style={styles.methodCopy}><Text style={styles.methodTitle}>اختر عنوان التوصيل</Text><Text style={styles.methodText}>اضغط هنا لاختيار أو إضافة عنوان جديد لحساب رسوم الشحن بدقة.</Text></View></TouchableOpacity></View>
</ScrollView><View style={styles.bottom}><TouchableOpacity style={[styles.submit, submitting && styles.submitDisabled]} disabled={submitting} onPress={submit}><Text style={styles.submitText}>{submitting ? "جارِ إنشاء الدردشة..." : "تأكيد وإنشاء الطلب"}</Text><MaterialIcons name="arrow-back" size={21} color="#FFFFFF" /></TouchableOpacity></View></ScreenContainer>;
}
const styles = StyleSheet.create({
  header: { height: 54, backgroundColor: "#FFF", paddingHorizontal: 16, flexDirection: "row", alignItems: "center", justifyContent: "space-between", borderBottomWidth: 1, borderColor: "#F5F5F5" },
  headerTitle: { color: "#111", fontSize: 16, fontWeight: "900" },
  content: { padding: 16, paddingBottom: 100 },
  card: { backgroundColor: "#FFF", padding: 16, marginBottom: 12, borderRadius: 12, alignItems: "flex-end", shadowColor: "#000", shadowOpacity: 0.03, shadowRadius: 8, elevation: 2 },
  cardTitle: { color: "#111", fontSize: 15, fontWeight: "900", marginBottom: 16 },
  itemLine: { width: "100%", flexDirection: "row-reverse", justifyContent: "space-between", marginBottom: 12, gap: 12 },
  lineValue: { color: "#111", fontSize: 13, fontWeight: "700" },
  lineCopy: { flex: 1, alignItems: "flex-end" },
  lineLabel: { color: "#333", fontSize: 13, textAlign: "right", fontWeight: "500" },
  variant: { color: "#777", fontSize: 11, marginTop: 4 },
  divider: { height: 1, backgroundColor: "#F0F0F0", width: "100%", marginVertical: 8 },
  total: { color: "#E60023", fontSize: 18, fontWeight: "900" },
  totalLabel: { color: "#111", fontSize: 16, fontWeight: "900" },
  method: { flexDirection: "row-reverse", gap: 12, alignItems: "flex-start", width: "100%" },
  methodCopy: { flex: 1, alignItems: "flex-end" },
  methodTitle: { color: "#111", fontSize: 14, fontWeight: "800" },
  methodText: { color: "#777", fontSize: 12, lineHeight: 20, textAlign: "right", marginTop: 4 },
  bottom: { position: "absolute", bottom: 0, left: 0, right: 0, backgroundColor: "#FFF", padding: 16, borderTopWidth: 1, borderColor: "#F0F0F0" },
  submit: { height: 48, borderRadius: 24, backgroundColor: "#111", flexDirection: "row-reverse", gap: 8, alignItems: "center", justifyContent: "center" },
  submitDisabled: { backgroundColor: "#CCC" },
  submitText: { color: "#FFF", fontSize: 14, fontWeight: "800" },
});
