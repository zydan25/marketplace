import { Share, TouchableOpacity, StyleSheet } from "react-native";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import Constants from "expo-constants";

export function ShareButton({ type, id, title }: { type: "product" | "store"; id: string; title: string }) {
  const scheme = Constants.expoConfig?.scheme || "manus";
  
  async function handleShare() {
    try {
      const url = `${scheme}://${type}/${id}`;
      const message = type === "product" 
        ? `شاهد هذا المنتج الرائع: ${title}\n${url}`
        : `تسوق من متجر: ${title}\n${url}`;
        
      await Share.share({
        message,
        url, // Used on iOS
        title: `مشاركة ${title}`
      });
    } catch (error) {
      console.error(error);
    }
  }

  return (
    <TouchableOpacity style={styles.button} onPress={handleShare}>
      <MaterialIcons name="share" size={24} color="#111" />
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  button: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "#F5F5F5",
    alignItems: "center",
    justifyContent: "center",
  }
});
