import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { Alert, Image, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import { useEffect } from "react";
import { ScreenContainer } from "@/components/screen-container";
import { useAuth } from "@/hooks/use-auth";
const later = (title:string) => Alert.alert(title,"ستتوفر هذه الميزة ضمن حسابك قريبًا.");
export default function ProfileScreen() { const {user,isAuthenticated,logout}=useAuth(); useEffect(() => { if (user?.role === "vendor") router.replace("/vendor" as never); }, [user?.role]); if(user?.role === "vendor") return null; if(!isAuthenticated) return <Guest/>; const name=user?.name?.trim()||"التخفيض الصح"; const admin=user?.role==="admin"; return <ScreenContainer edges={["top","left","right"]} className="bg-[#F5F5F5]"><ScrollView contentContainerStyle={s.content}><View style={s.head}><TouchableOpacity onPress={()=>router.push("/settings" as never)}><MaterialIcons name="settings" size={27}/></TouchableOpacity><TouchableOpacity onPress={()=>later("رمز حسابي")}><MaterialIcons name="qr-code-scanner" size={27}/></TouchableOpacity><View style={s.identity}><View style={s.avatar}><Text style={s.avatarText}>{name.slice(0,1)}</Text></View><View><Text style={s.name}>{name}</Text><Text style={s.personal}>ملفي الشخصي <MaterialIcons name="edit-note" size={13}/></Text></View></View></View><View style={s.wallet}><Metric icon="confirmation-number" label="كوبونات" value="0"/><Metric icon="stars" label="نقاط" value="0"/><Metric icon="account-balance-wallet" label="محفظة" value="0 ر.ي"/><Metric icon="card-giftcard" label="بطاقة هدية" value=""/><View style={s.coupon}><MaterialIcons name="local-offer" color="#E60023" size={20}/><Text style={s.couponText}>انتهز فرصة الكوبونات — ستظهر الخصومات المفعلة هنا</Text></View></View><Panel title="طلباتي" action="عرض الكل" onAction={()=>router.push("/orders" as never)}><Action icon="credit-card" label="غير مدفوع"/><Action icon="inventory-2" label="قيد التجهيز"/><Action icon="local-shipping" label="تم الشحن"/><Action icon="rate-review" label="تعليق"/></Panel><View style={s.panel}><Action icon="support-agent" label="تواصل معنا" onPress={()=>router.push("/support" as never)}/>
<Action icon="card-giftcard" label="إرسال هدية" onPress={()=>router.push("/extra-features" as never)}/>
<Action icon="analytics" label="تقارير الحساب" onPress={()=>router.push("/customer-reports" as never)}/><Action icon="event-available" label="تسجيل الحضور"/><Action icon="verified-user" label="السياسة"/><Action icon="share" label="دعوة" onPress={()=>router.push("/invite" as never)}/></View><View style={s.metrics}><Text style={s.metric}>متابع{`\n`}<Text style={s.metricSmall}>0 متابع</Text></Text><Text style={s.metric}>تاريخ{`\n`}<Text style={s.metricSmall}>0 منتج</Text></Text><Text style={s.metric}>قائمة أمانياتي{`\n`}<Text style={s.metricSmall}>0 صنف</Text></Text></View><View style={s.favorites}><MaterialIcons name="favorite-border" size={34} color="#E60023"/><Text style={s.favTitle}>منتجاتك المفضلة ستظهر هنا</Text><Text style={s.favText}>بعد إضافة الفئات والأصناف، ستظهر لك العروض المناسبة.</Text></View>{admin?<TouchableOpacity style={s.admin} onPress={()=>router.push("/admin" as never)}><MaterialIcons name="admin-panel-settings" size={24} color="#F0B800"/><Text style={s.adminText}>لوحة التحكم بالإدارة</Text></TouchableOpacity>:null}<TouchableOpacity style={s.logout} onPress={logout}><MaterialIcons name="logout" size={22} color="#BB3F46"/><Text style={s.logoutText}>تسجيل الخروج</Text></TouchableOpacity></ScrollView></ScreenContainer>; }
function Guest(){return <ScreenContainer edges={["top","bottom","left","right"]} className="bg-[#FCFBF8]"><View style={s.guest}><Image source={require("@/assets/images/icon.png")} style={s.guestLogo}/><Text style={s.guestTitle}>أهلاً بك في التخفيض الصح</Text><Text style={s.guestSub}>سجل الدخول للوصول إلى طلباتك وكوبوناتك ومزايا حسابك.</Text><TouchableOpacity style={s.guestButton} onPress={()=>router.push("/login" as never)}><Text style={s.guestButtonText}>تسجيل الدخول</Text></TouchableOpacity></View></ScreenContainer>}
function Metric({icon,label,value}:{icon:any;label:string;value:string}){return <TouchableOpacity style={s.walletItem} onPress={()=>later(label)}><MaterialIcons name={icon} size={24} color="#333"/>{value?<Text style={s.value}>{value}</Text>:null}<Text style={s.walletLabel}>{label}</Text></TouchableOpacity>}; function Action({icon,label,onPress}:{icon:any;label:string;onPress?:()=>void}){return <TouchableOpacity style={s.action} onPress={onPress||(()=>later(label))}><MaterialIcons name={icon} size={24} color="#333"/><Text style={s.actionText}>{label}</Text></TouchableOpacity>}; function Panel({title,action,onAction,children}:{title:string;action:string;onAction:()=>void;children:React.ReactNode}){return <View style={s.orders}><View style={s.panelTop}><TouchableOpacity onPress={onAction}><Text style={s.all}>{action} ‹</Text></TouchableOpacity><Text style={s.panelTitle}>{title}</Text></View><View style={s.actions}>{children}</View></View>}
const s=StyleSheet.create({
  content: { paddingBottom: 40 },
  head: { backgroundColor: "#FFF", padding: 16, paddingTop: 20, flexDirection: "row", gap: 16, alignItems: "center", borderBottomWidth: 1, borderColor: "#F5F5F5" },
  identity: { marginLeft: "auto", flexDirection: "row-reverse", gap: 12, alignItems: "center" },
  avatar: { width: 48, height: 48, borderRadius: 24, backgroundColor: "#F5F5F5", alignItems: "center", justifyContent: "center" },
  avatarText: { fontSize: 20, fontWeight: "900", color: "#111" },
  name: { fontSize: 16, fontWeight: "900", textAlign: "right", color: "#111" },
  personal: { color: "#777", fontSize: 11, textAlign: "right", marginTop: 2 },
  wallet: { margin: 12, backgroundColor: "#FFF", flexDirection: "row-reverse", flexWrap: "wrap", borderRadius: 12, paddingTop: 16, shadowColor: "#000", shadowOpacity: 0.03, shadowRadius: 8, elevation: 2 },
  walletItem: { width: "25%", alignItems: "center", minHeight: 64 },
  value: { fontSize: 15, fontWeight: "900", color: "#111", marginTop: 2 },
  walletLabel: { fontSize: 10, color: "#555", marginTop: 4 },
  coupon: { width: "100%", borderTopWidth: 1, borderColor: "#F5F5F5", padding: 12, flexDirection: "row-reverse", alignItems: "center", gap: 8 },
  couponText: { fontSize: 11, color: "#794F1A", flex: 1, textAlign: "right" },
  orders: { marginHorizontal: 12, backgroundColor: "#FFF", borderRadius: 12, marginTop: 4, shadowColor: "#000", shadowOpacity: 0.03, shadowRadius: 8, elevation: 2 },
  panel: { marginHorizontal: 12, marginTop: 12, backgroundColor: "#FFF", paddingVertical: 16, flexDirection: "row-reverse", borderRadius: 12, shadowColor: "#000", shadowOpacity: 0.03, shadowRadius: 8, elevation: 2 },
  panelTop: { paddingHorizontal: 16, paddingTop: 16, flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  panelTitle: { fontSize: 15, fontWeight: "900", color: "#111" },
  all: { color: "#777", fontSize: 12 },
  actions: { flexDirection: "row-reverse", paddingVertical: 16 },
  action: { flex: 1, alignItems: "center" },
  actionText: { fontSize: 10, color: "#555", textAlign: "center", marginTop: 6 },
  metrics: { margin: 12, backgroundColor: "#FFF", borderRadius: 12, paddingVertical: 16, flexDirection: "row-reverse", justifyContent: "space-around", shadowColor: "#000", shadowOpacity: 0.03, shadowRadius: 8, elevation: 2 },
  metric: { fontSize: 13, fontWeight: "900", color: "#111", textAlign: "center", lineHeight: 20 },
  metricSmall: { fontSize: 10, fontWeight: "400", color: "#777" },
  favorites: { margin: 12, padding: 24, backgroundColor: "#FFF", borderRadius: 12, alignItems: "center", borderStyle: "dashed", borderWidth: 1, borderColor: "#DDD" },
  favTitle: { fontSize: 14, fontWeight: "900", color: "#111", marginTop: 8 },
  favText: { color: "#777", fontSize: 11, marginTop: 4, textAlign: "center" },
  admin: { height: 48, margin: 12, backgroundColor: "#111", borderRadius: 12, flexDirection: "row-reverse", justifyContent: "center", alignItems: "center", gap: 8 },
  adminText: { color: "#FFF", fontSize: 14, fontWeight: "900" },
  logout: { alignSelf: "center", padding: 16, flexDirection: "row-reverse", gap: 6, marginTop: 8 },
  logoutText: { color: "#E60023", fontSize: 13, fontWeight: "700" },
  guest: { flex: 1, justifyContent: "center", alignItems: "center", paddingHorizontal: 32 },
  guestLogo: { width: 80, height: 80, borderRadius: 20, marginBottom: 24 },
  guestTitle: { fontSize: 22, fontWeight: "900", color: "#111", textAlign: "center" },
  guestSub: { fontSize: 13, color: "#777", textAlign: "center", lineHeight: 22, marginTop: 8 },
  guestButton: { marginTop: 32, width: "100%", maxWidth: 300, height: 48, borderRadius: 12, backgroundColor: "#111", alignItems: "center", justifyContent: "center" },
  guestButtonText: { color: "#FFF", fontSize: 15, fontWeight: "800" }
});
