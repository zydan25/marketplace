import { useEffect } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { ScreenContainer } from "@/components/screen-container";

export default function VendorDesignRedirect() {
  useEffect(() => { router.replace("/vendor/storefront" as never); }, []);
  return <ScreenContainer className="bg-[#F6F6F6]"><View style={styles.center}><ActivityIndicator color="#E60023"/><Text style={styles.text}>جارٍ فتح محرر واجهة المتجر...</Text></View></ScreenContainer>;
}
const styles=StyleSheet.create({center:{flex:1,alignItems:"center",justifyContent:"center",gap:10},text:{fontSize:12,color:"#777"}});
