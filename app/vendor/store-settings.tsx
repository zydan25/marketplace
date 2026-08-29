import * as ImagePicker from "expo-image-picker";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { useEffect, useState } from "react";
import { ActivityIndicator, Alert, Image, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";

import { ScreenContainer } from "@/components/screen-container";
import { djangoApi } from "@/lib/django-api";

type Vendor = {
  id: number; store_name: string; slug: string; description: string; phone: string; address: string; status: string;
  logo_url?: string | null; cover_url?: string | null; settings?: Record<string, unknown>;
};

function toDataUrl(asset: ImagePicker.ImagePickerAsset) {
  if (!asset.base64) return "";
  return `data:${asset.mimeType ?? "image/jpeg"};base64,${asset.base64}`;
}

export default function VendorStoreSettingsScreen() {
  const [vendor, setVendor] = useState<Vendor | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [logo, setLogo] = useState("");
  const [cover, setCover] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    djangoApi<{ results?: Vendor[] }>("/api/vendors/")
      .then((result) => {
        const current = result.results?.[0] ?? null;
        setVendor(current);
        setName(current?.store_name ?? "");
        setDescription(current?.description ?? "");
        setPhone(current?.phone ?? "");
        setAddress(current?.address ?? "");
        setLogo(current?.logo_url ?? "");
        setCover(current?.cover_url ?? "");
      })
      .catch((error) => Alert.alert("تعذر تحميل بيانات المتجر", error instanceof Error ? error.message : "حاول مرة أخرى."))
      .finally(() => setLoading(false));
  }, []);

  async function pick(kind: "logo" | "cover") {
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], allowsEditing: true, quality: 0.82, base64: true });
    const asset = result.assets?.[0];
    if (result.canceled || !asset?.base64) return;
    const dataUrl = toDataUrl(asset);
    if (kind === "logo") setLogo(dataUrl); else setCover(dataUrl);
  }

  async function save() {
    if (!vendor) return;
    if (!name.trim()) return Alert.alert("اسم المتجر مطلوب", "اكتب اسم المتجر.");
    setSaving(true);
    try {
      const updated = await djangoApi<Vendor>(`/api/vendors/${encodeURIComponent(vendor.slug)}/`, {
        method: "PATCH",
        body: JSON.stringify({
          store_name: name.trim(), description: description.trim(), phone: phone.trim(), address: address.trim(),
          ...(logo.startsWith("data:image/") ? { logo_data_url: logo } : {}),
          ...(cover.startsWith("data:image/") ? { cover_data_url: cover } : {}),
        }),
      });
      setVendor(updated);
      setName(updated.store_name);
      setDescription(updated.description ?? "");
      setPhone(updated.phone ?? "");
      setAddress(updated.address ?? "");
      setLogo(updated.logo_url ?? logo);
      setCover(updated.cover_url ?? cover);
      Alert.alert("تم الحفظ", "تم تحديث بيانات المتجر بنجاح.");
    } catch (error) {
      Alert.alert("تعذر حفظ المتجر", error instanceof Error ? error.message : "تحقق من الصلاحيات والبيانات.");
    } finally { setSaving(false); }
  }

  if (loading) return <ScreenContainer><View style={styles.center}><ActivityIndicator color="#E60023"/><Text style={styles.muted}>جارٍ تحميل بيانات متجرك...</Text></View></ScreenContainer>;
  if (!vendor) return <ScreenContainer><View style={styles.center}><Text style={styles.empty}>لا يوجد متجر مرتبط بهذا الحساب أو أن الحساب لم يُعتمد بعد.</Text><TouchableOpacity style={styles.backBtn} onPress={() => router.back()}><Text style={styles.backText}>العودة</Text></TouchableOpacity></View></ScreenContainer>;

  return <ScreenContainer className="bg-[#F6F7F9]" edges={["top","bottom","left","right"]}>
    <View style={styles.header}><TouchableOpacity onPress={() => router.back()}><MaterialIcons name="arrow-forward" size={24} color="#111"/></TouchableOpacity><Text style={styles.title}>بيانات المتجر</Text><View style={{width:24}}/></View>
    <ScrollView contentContainerStyle={styles.page} keyboardShouldPersistTaps="handled">
      <View style={styles.card}><Text style={styles.section}>هوية المتجر</Text><Text style={styles.label}>اسم المتجر</Text><TextInput value={name} onChangeText={setName} style={styles.input} textAlign="right"/><Text style={styles.label}>وصف المتجر</Text><TextInput value={description} onChangeText={setDescription} style={[styles.input,styles.multiline]} multiline textAlign="right"/><Text style={styles.label}>رقم التواصل</Text><TextInput value={phone} onChangeText={setPhone} style={styles.input} keyboardType="phone-pad" textAlign="right"/><Text style={styles.label}>العنوان</Text><TextInput value={address} onChangeText={setAddress} style={styles.input} textAlign="right"/></View>
      <View style={styles.card}><Text style={styles.section}>الشعار والغلاف</Text><TouchableOpacity style={styles.media} onPress={()=>pick("logo")}><View style={styles.mediaPreview}>{logo?<Image source={{uri:logo}} style={styles.logo}/>:<MaterialIcons name="storefront" size={28} color="#888"/>}</View><View style={styles.mediaCopy}><Text style={styles.mediaTitle}>شعار المتجر</Text><Text style={styles.mediaHint}>صورة مربعة واضحة لعلامة المتجر</Text></View><MaterialIcons name="add-photo-alternate" size={22} color="#111"/></TouchableOpacity><TouchableOpacity style={styles.media} onPress={()=>pick("cover")}><View style={styles.coverPreview}>{cover?<Image source={{uri:cover}} style={styles.coverImage}/>:<MaterialIcons name="image" size={25} color="#888"/>}</View><View style={styles.mediaCopy}><Text style={styles.mediaTitle}>غلاف المتجر</Text><Text style={styles.mediaHint}>صورة عريضة تظهر أعلى صفحة المتجر</Text></View><MaterialIcons name="add-photo-alternate" size={22} color="#111"/></TouchableOpacity></View>
      <View style={styles.status}><View style={[styles.dot,{backgroundColor:vendor.status==="active"?"#16A34A":"#F59E0B"}]}/><Text style={styles.statusText}>{vendor.status==="active"?"متجرك نشط ويظهر للعملاء":"متجرك قيد المراجعة أو موقوف"}</Text></View>
      <TouchableOpacity style={[styles.save,saving&&styles.disabled]} disabled={saving} onPress={save}><Text style={styles.saveText}>{saving?"جارٍ الحفظ...":"حفظ بيانات المتجر"}</Text></TouchableOpacity>
    </ScrollView>
  </ScreenContainer>;
}

const styles=StyleSheet.create({header:{height:60,paddingHorizontal:16,backgroundColor:"#FFF",flexDirection:"row",justifyContent:"space-between",alignItems:"center",borderBottomWidth:1,borderColor:"#EEE"},title:{fontSize:18,fontWeight:"900",color:"#111"},page:{padding:12,paddingBottom:80,maxWidth:760,width:"100%",alignSelf:"center"},card:{backgroundColor:"#FFF",borderRadius:15,padding:15,marginBottom:12},section:{fontSize:17,fontWeight:"900",color:"#111",textAlign:"right",marginBottom:15},label:{fontSize:11,fontWeight:"800",color:"#555",textAlign:"right",marginBottom:6},input:{backgroundColor:"#F7F7F8",borderWidth:1,borderColor:"#E4E4E7",borderRadius:10,paddingHorizontal:12,paddingVertical:11,fontSize:13,color:"#111",marginBottom:12},multiline:{minHeight:90,textAlignVertical:"top"},media:{flexDirection:"row-reverse",alignItems:"center",gap:10,borderWidth:1,borderColor:"#E8E8E8",borderRadius:12,padding:10,marginBottom:9},mediaPreview:{width:58,height:58,borderRadius:12,backgroundColor:"#F2F2F2",alignItems:"center",justifyContent:"center",overflow:"hidden"},logo:{width:"100%",height:"100%"},coverPreview:{width:84,height:58,borderRadius:10,backgroundColor:"#F2F2F2",alignItems:"center",justifyContent:"center",overflow:"hidden"},coverImage:{width:"100%",height:"100%"},mediaCopy:{flex:1,alignItems:"flex-end"},mediaTitle:{fontSize:12,fontWeight:"900",color:"#111"},mediaHint:{fontSize:9,color:"#888",marginTop:3,textAlign:"right"},status:{flexDirection:"row-reverse",alignItems:"center",justifyContent:"center",gap:7,marginBottom:12},dot:{width:8,height:8,borderRadius:4},statusText:{fontSize:10,color:"#666",fontWeight:"800"},save:{height:48,borderRadius:24,backgroundColor:"#111",alignItems:"center",justifyContent:"center"},disabled:{opacity:.55},saveText:{color:"#FFF",fontWeight:"900"},center:{flex:1,alignItems:"center",justifyContent:"center",padding:25,gap:10},muted:{color:"#777",fontSize:12},empty:{color:"#666",fontSize:13,textAlign:"center",lineHeight:21},backBtn:{marginTop:10,backgroundColor:"#111",paddingHorizontal:20,paddingVertical:10,borderRadius:20},backText:{color:"#FFF",fontWeight:"800"}});
