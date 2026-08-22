import { useEffect, useState } from "react";
import { Alert, FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ScreenContainer } from "@/components/screen-container";
import { ApiClient } from "@/lib/api-client";

type Address = { id: number; title: string; city: { name: string }; district: string; street: string; phone: string; is_default: boolean };

export default function AddressesScreen() {
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const data = await ApiClient.get<{ results: Address[] }>("/api/addresses/");
      setAddresses(data.results || []);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  function selectAddress(address: Address) {
    // Here we would typically save to context or pass back via router params
    Alert.alert("تم الاختيار", `تم اختيار عنوان: ${address.title}`);
    router.back();
  }

  return (
    <ScreenContainer edges={["top", "bottom", "left", "right"]} className="bg-[#F5F5F5]">
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}><MaterialIcons name="arrow-forward" size={25} /></TouchableOpacity>
        <Text style={styles.title}>عناويني</Text>
        <TouchableOpacity onPress={() => Alert.alert("قريباً", "إضافة عنوان جديد ستتوفر قريباً")}><MaterialIcons name="add" size={25} color="#E60023" /></TouchableOpacity>
      </View>
      
      <FlatList
        style={{ flex: 1 }}
        data={addresses}
        keyExtractor={item => String(item.id)}
        contentContainerStyle={styles.list}
        ListEmptyComponent={<Text style={styles.empty}>لا توجد عناوين محفوظة.</Text>}
        renderItem={({ item }) => (
          <TouchableOpacity style={styles.card} onPress={() => selectAddress(item)}>
            <View style={styles.cardHeader}>
              <Text style={styles.cardTitle}>{item.title}</Text>
              {item.is_default && <View style={styles.badge}><Text style={styles.badgeText}>الافتراضي</Text></View>}
            </View>
            <Text style={styles.details}>{item.city.name} - {item.district}</Text>
            <Text style={styles.details}>{item.street}</Text>
            <Text style={styles.phone}>{item.phone}</Text>
          </TouchableOpacity>
        )}
      />
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  header: { padding: 16, backgroundColor: "#FFF", flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  title: { fontSize: 20, fontWeight: "900" },
  list: { padding: 14, paddingBottom: 180 },
  card: { backgroundColor: "#FFF", borderRadius: 10, padding: 16, marginBottom: 12, alignItems: "flex-end" },
  cardHeader: { flexDirection: "row-reverse", justifyContent: "space-between", width: "100%", marginBottom: 8 },
  cardTitle: { fontSize: 16, fontWeight: "900" },
  badge: { backgroundColor: "#E6F4FE", paddingHorizontal: 8, paddingVertical: 4, borderRadius: 4 },
  badgeText: { color: "#0a7ea4", fontSize: 10, fontWeight: "700" },
  details: { color: "#555", fontSize: 13, marginBottom: 4, textAlign: "right" },
  phone: { color: "#111", fontSize: 13, fontWeight: "700", marginTop: 4, textAlign: "right", writingDirection: "ltr" },
  empty: { textAlign: "center", color: "#777", marginTop: 40 },
});
