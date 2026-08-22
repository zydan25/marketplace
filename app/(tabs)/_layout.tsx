import { Tabs } from "expo-router";
import { Platform } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { HapticTab } from "@/components/haptic-tab";
import { IconSymbol } from "@/components/ui/icon-symbol";

export default function TabLayout() {
  const insets = useSafeAreaInsets();
  const bottomPadding = Platform.OS === "web" ? 12 : Math.max(insets.bottom, 8);
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: "#111111",
        tabBarInactiveTintColor: "rgba(0,0,0,0.40)",
        tabBarButton: HapticTab,
        tabBarStyle: {
          height: 58 + bottomPadding,
          paddingTop: 7,
          paddingBottom: bottomPadding,
          backgroundColor: "#FFFFFF",
          borderTopWidth: 1,
          borderTopColor: "#EEEEEE",
          elevation: 0,
          shadowOpacity: 0,
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
        },
        tabBarLabelStyle: { fontSize: 9, fontWeight: "700", marginTop: 3 },
      }}
    >
      <Tabs.Screen name="index" options={{ title: "الرئيسية", tabBarIcon: ({ color }) => <IconSymbol name="house.fill" size={21} color={color} /> }} />
      <Tabs.Screen name="categories" options={{ title: "الفئات", tabBarIcon: ({ color }) => <IconSymbol name="square.grid.2x2.fill" size={21} color={color} /> }} />
      <Tabs.Screen name="trends" options={{ title: "ترند", tabBarIcon: ({ color }) => <IconSymbol name="sparkles" size={21} color={color} /> }} />
      <Tabs.Screen name="bag" options={{ title: "السلة", tabBarIcon: ({ color }) => <IconSymbol name="bag.fill" size={21} color={color} /> }} />
      <Tabs.Screen name="profile" options={{ title: "حسابي", tabBarIcon: ({ color }) => <IconSymbol name="person.fill" size={21} color={color} /> }} />
      <Tabs.Screen name="vendors" options={{ href: null }} />
    </Tabs>
  );
}
