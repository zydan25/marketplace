import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Alert, ActivityIndicator, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import { formatYER } from "@/lib/catalog";
import { useCart } from "@/lib/cart-context";
import { ScreenContainer } from "@/components/screen-container";
import { createOrder } from "@/lib/order-api";
import { djangoApi } from "@/lib/django-api";

type Address = { id:number; title:string; city?:{id?:number;name:string}; district:string; street:string; phone:string; is_default:boolean };
type ServerCart = { valid?:boolean; subtotal?:string|number; shipping_fee?:string|number; discount?:string|number; total?:string|number; errors?:string[] };

export default function CheckoutScreen(){
  const insets = useSafeAreaInsets();
  const {items,removeItem,validateCartWithServer}=useCart();
  const {lines}=useLocalSearchParams<{lines?:string}>();
  const selectedIds=useMemo(()=>new Set((lines??"").split(",").filter(Boolean)),[lines]);
  const orderItems=selectedIds.size?items.filter(i=>selectedIds.has(i.lineId)):items;
  const [submitting,setSubmitting]=useState(false), [loadingAddresses,setLoadingAddresses]=useState(true), [addresses,setAddresses]=useState<Address[]>([]), [selectedAddressId,setSelectedAddressId]=useState<number|null>(null), [couponCode,setCouponCode]=useState(""), [serverData,setServerData]=useState<ServerCart|null>(null);

  useEffect(()=>{
    djangoApi<{results?:Address[]}|Address[]>("/api/addresses/").then(data=>{const list=Array.isArray(data)?data:(data.results??[]);setAddresses(list);setSelectedAddressId(list.find(x=>x.is_default)?.id??list[0]?.id??null)}).catch(()=>setAddresses([])).finally(()=>setLoadingAddresses(false));
  },[]);
  useEffect(()=>{if(!orderItems.length||(addresses.length>0&&selectedAddressId==null))return;const cityId=addresses.find(x=>x.id===selectedAddressId)?.city?.id;validateCartWithServer(cityId,couponCode).then(setServerData).catch(()=>setServerData(null));},[orderItems.length,selectedAddressId,addresses,couponCode,validateCartWithServer]);
  const subtotal=Number(serverData?.subtotal??orderItems.reduce((t,i)=>t+i.unitPrice*i.quantity,0)), shipping=Number(serverData?.shipping_fee??0), discount=Number(serverData?.discount??0), total=Number(serverData?.total??subtotal+shipping-discount);
  const selectedAddress=addresses.find(x=>x.id===selectedAddressId);

  async function submit(){
    if(!orderItems.length)return Alert.alert("الحقيبة فارغة","أضف منتجًا واحدًا على الأقل قبل إكمال الطلب.");
    if(!selectedAddress)return Alert.alert("العنوان مطلوب","اختر عنوان التوصيل قبل تأكيد الطلب.");
    try{
      setSubmitting(true);
      const validation=await validateCartWithServer(selectedAddress.city?.id,couponCode); setServerData(validation);
      if(validation?.valid===false){Alert.alert("تحديث في السلة",validation.errors?.join("\n")||"تغيرت بعض المنتجات أو الأسعار.");return;}
      const order=await createOrder(orderItems.map(item=>({productId:Number(item.product.id),variantId:item.variantId,color:item.color,size:item.size,quantity:item.quantity})),{address_id:selectedAddress.id,city_id:selectedAddress.city?.id,title:selectedAddress.title,district:selectedAddress.district,street:selectedAddress.street,phone:selectedAddress.phone},"YER",couponCode);
      orderItems.forEach(item=>removeItem(item.lineId));
      router.replace(`/order-chat/${order.id}` as never);
    }catch(error){Alert.alert("تعذر إنشاء الطلب",error instanceof Error?error.message:"سجّل الدخول ثم حاول مرة أخرى.");}finally{setSubmitting(false);}
  }

  return <ScreenContainer edges={["top","bottom","left","right"]} className="bg-[#F6F6F6]">
    <View style={styles.header}><TouchableOpacity onPress={()=>router.back()}><MaterialIcons name="close" size={24} color="#171717"/></TouchableOpacity><Text style={styles.headerTitle}>مراجعة الطلب</Text><View style={{width:24}}/></View>
    <ScrollView style={{flex:1}} contentContainerStyle={[styles.content,{paddingBottom:130+insets.bottom}]} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator>
      <View style={styles.card}><Text style={styles.cardTitle}>الأصناف المحددة ({orderItems.reduce((n,item)=>n+item.quantity,0)})</Text>{orderItems.map(item=><View key={item.lineId} style={styles.itemLine}><Text style={styles.lineValue}>{formatYER(item.unitPrice*item.quantity)}</Text><View style={styles.lineCopy}><Text style={styles.lineLabel}>{item.quantity} × {item.product.name}</Text><Text style={styles.variant}>{item.color||""}{item.size?` · ${item.size}`:""}</Text></View></View>)}</View>
      <View style={styles.card}><View style={styles.rowBetween}><Text style={styles.cardTitle}>عنوان التوصيل</Text><TouchableOpacity onPress={()=>router.push("/addresses" as never)}><Text style={styles.link}>إدارة العناوين</Text></TouchableOpacity></View>{loadingAddresses?<ActivityIndicator color="#E60023"/>:addresses.length===0?<TouchableOpacity onPress={()=>router.push("/addresses" as never)}><Text style={styles.emptyAddress}>لا يوجد عنوان محفوظ. أضف عنوانًا أولًا.</Text></TouchableOpacity>:addresses.map(address=><TouchableOpacity key={address.id} onPress={()=>setSelectedAddressId(address.id)} style={[styles.address,selectedAddressId===address.id&&styles.addressSelected]}><View style={styles.addressRadio}>{selectedAddressId===address.id?<MaterialIcons name="check" size={15} color="#FFF"/>:null}</View><View style={styles.addressCopy}><Text style={styles.addressTitle}>{address.title}{address.is_default?" · الافتراضي":""}</Text><Text style={styles.addressText}>{address.city?.name??""} - {address.district}</Text><Text style={styles.addressText}>{address.street} · {address.phone}</Text></View></TouchableOpacity>)}</View>
      <View style={styles.card}><Text style={styles.cardTitle}>كوبون الخصم</Text><View style={styles.couponRow}><TextInput value={couponCode} onChangeText={setCouponCode} placeholder="أدخل رمز الكوبون" autoCapitalize="characters" style={styles.couponInput}/><TouchableOpacity onPress={()=>validateCartWithServer(selectedAddress?.city?.id,couponCode).then(setServerData).catch(()=>undefined)} style={styles.couponButton}><Text style={styles.couponButtonText}>تطبيق</Text></TouchableOpacity></View></View>
      <View style={styles.card}><Text style={styles.cardTitle}>ملخص الدفع</Text><SummaryRow label="المجموع الفرعي" value={subtotal}/><SummaryRow label="الشحن" value={shipping}/><SummaryRow label="الخصم" value={-discount}/><View style={styles.divider}/><SummaryRow label="الإجمالي النهائي" value={total} strong/></View>
      <View style={styles.card}><Text style={styles.cardTitle}>طريقة الدفع</Text><View style={styles.method}><MaterialIcons name="payments" size={23} color="#E60023"/><View style={styles.methodCopy}><Text style={styles.methodTitle}>الدفع عند الاستلام</Text><Text style={styles.methodText}>سيتم تثبيت المبلغ والدفع عند تسليم الطلب.</Text></View></View></View>
    </ScrollView>
    <View style={[styles.bottom,{paddingBottom:Math.max(insets.bottom,10)}]}><TouchableOpacity style={[styles.submit,submitting&&styles.submitDisabled]} disabled={submitting} onPress={submit}><Text style={styles.submitText}>{submitting?"جارٍ إنشاء الطلب...":`تأكيد الطلب · ${formatYER(total)}`}</Text><MaterialIcons name="arrow-back" size={21} color="#FFF"/></TouchableOpacity></View>
  </ScreenContainer>
}
function SummaryRow({label,value,strong=false}:{label:string;value:number;strong?:boolean}){return <View style={styles.summaryRow}><Text style={[styles.summaryValue,strong&&styles.totalValue]}>{formatYER(value)}</Text><Text style={[styles.summaryLabel,strong&&styles.totalLabel]}>{label}</Text></View>}
const styles=StyleSheet.create({header:{height:54,backgroundColor:"#FFF",paddingHorizontal:16,flexDirection:"row",alignItems:"center",justifyContent:"space-between",borderBottomWidth:1,borderColor:"#F5F5F5"},headerTitle:{color:"#111",fontSize:16,fontWeight:"900"},content:{padding:16},card:{backgroundColor:"#FFF",padding:16,marginBottom:12,borderRadius:12,alignItems:"flex-end"},cardTitle:{color:"#111",fontSize:15,fontWeight:"900",marginBottom:14},rowBetween:{width:"100%",flexDirection:"row",justifyContent:"space-between",alignItems:"center"},link:{color:"#E60023",fontSize:11,fontWeight:"800"},itemLine:{width:"100%",flexDirection:"row-reverse",justifyContent:"space-between",marginBottom:12,gap:12},lineValue:{color:"#111",fontSize:13,fontWeight:"700"},lineCopy:{flex:1,alignItems:"flex-end"},lineLabel:{color:"#333",fontSize:13,textAlign:"right",fontWeight:"500"},variant:{color:"#777",fontSize:11,marginTop:4},address:{width:"100%",flexDirection:"row-reverse",gap:10,padding:12,borderWidth:1,borderColor:"#EEE",borderRadius:10,marginBottom:8,alignItems:"center"},addressSelected:{borderColor:"#111",backgroundColor:"#FAFAFA"},addressRadio:{width:24,height:24,borderRadius:12,backgroundColor:"#111",alignItems:"center",justifyContent:"center"},addressCopy:{flex:1,alignItems:"flex-end"},addressTitle:{fontSize:13,fontWeight:"900",color:"#111"},addressText:{fontSize:11,color:"#666",marginTop:3,textAlign:"right"},emptyAddress:{color:"#777",fontSize:12,textAlign:"right"},couponRow:{width:"100%",flexDirection:"row-reverse",gap:8},couponInput:{flex:1,height:44,borderWidth:1,borderColor:"#EEE",borderRadius:10,paddingHorizontal:12,textAlign:"right",fontSize:13,backgroundColor:"#FAFAFA"},couponButton:{height:44,paddingHorizontal:16,borderRadius:10,backgroundColor:"#111",justifyContent:"center"},couponButtonText:{color:"#FFF",fontSize:12,fontWeight:"800"},summaryRow:{width:"100%",flexDirection:"row-reverse",justifyContent:"space-between",paddingVertical:5},summaryValue:{fontSize:13,fontWeight:"700",color:"#333"},summaryLabel:{fontSize:13,color:"#666"},totalValue:{fontSize:19,color:"#E60023",fontWeight:"900"},totalLabel:{fontSize:14,color:"#111",fontWeight:"900"},divider:{width:"100%",height:1,backgroundColor:"#F0F0F0",marginVertical:7},method:{width:"100%",flexDirection:"row-reverse",gap:12},methodCopy:{flex:1,alignItems:"flex-end"},methodTitle:{color:"#111",fontSize:14,fontWeight:"800"},methodText:{color:"#777",fontSize:12,lineHeight:20,textAlign:"right",marginTop:4},bottom:{position:"absolute",bottom:0,left:0,right:0,backgroundColor:"#FFF",paddingHorizontal:16,paddingTop:12,borderTopWidth:1,borderColor:"#F0F0F0"},submit:{height:48,borderRadius:24,backgroundColor:"#111",flexDirection:"row-reverse",gap:8,alignItems:"center",justifyContent:"center"},submitDisabled:{backgroundColor:"#CCC"},submitText:{color:"#FFF",fontSize:14,fontWeight:"800"}});