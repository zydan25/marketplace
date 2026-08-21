import { Tabs } from "expo-router";
import { Platform } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { HapticTab } from "@/components/haptic-tab";
import { IconSymbol } from "@/components/ui/icon-symbol";

export default function TabLayout() {
  const insets = useSafeAreaInsets();
  const bottomPadding = Platform.OS === "web" ? 16 : Math.max(insets.bottom, 8);
  return (
    <Tabs screenOptions={{
      headerShown: false,
      tabBarActiveTintColor: "#080808",
      tabBarInactiveTintColor: "rgba(0,0,0,0.46)",
      tabBarButton: HapticTab,
      tabBarStyle: { height: 60 + bottomPadding, paddingTop: 8, paddingBottom: bottomPadding, backgroundColor: "#FFFFFF", borderTopWidth: 1, borderTopColor: "#F0F0F0", elevation: 0, shadowOpacity: 0, position: "absolute", bottom: 0, left: 0, right: 0 },
      tabBarLabelStyle: { fontSize: 10, fontWeight: "600", marginTop: 4 },
    }}>
      <Tabs.Screen name="index" options={{ title: "الرئيسية", tabBarIcon: ({ color }) => <IconSymbol name="house.fill" size={22} color={color} /> }} />
      <Tabs.Screen name="categories" options={{ title: "الفئات", tabBarIcon: ({ color }) => <IconSymbol name="square.grid.2x2.fill" size={22} color={color} /> }} />
      <Tabs.Screen name="trends" options={{ title: "ترند", tabBarIcon: ({ color }) => <IconSymbol name="sparkles" size={22} color={color} /> }} />
      <Tabs.Screen name="bag" options={{ title: "السلة", tabBarIcon: ({ color }) => <IconSymbol name="bag.fill" size={22} color={color} /> }} />
      <Tabs.Screen name="profile" options={{ title: "حسابي", tabBarIcon: ({ color }) => <IconSymbol name="person.fill" size={22} color={color} /> }} />
    </Tabs>
  );
}
