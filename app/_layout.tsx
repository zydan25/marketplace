import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { I18nManager, Platform } from "react-native";
import { useEffect } from "react";

import { CartProvider } from "@/lib/cart-context";
import { ThemeProvider } from "@/lib/theme-provider";

I18nManager.allowRTL(true);

function DocumentDirection() {
  useEffect(() => {
    if (Platform.OS === "web" && typeof document !== "undefined") {
      document.documentElement.dir = "rtl";
      document.documentElement.lang = "ar";
    }
  }, []);
  return null;
}

export default function RootLayout() {
  return (
    <ThemeProvider>
      <CartProvider>
        <DocumentDirection />
        <StatusBar style="dark" />
        <Stack screenOptions={{ headerShown: false, animation: "slide_from_left" }}>
          <Stack.Screen name="(tabs)" />
          <Stack.Screen name="login" />
          <Stack.Screen name="register" />
          <Stack.Screen name="admin/index" />
          <Stack.Screen name="admin/products" />
          <Stack.Screen name="admin/storefront" />
          <Stack.Screen name="product/[id]" />
          <Stack.Screen name="search" />
          <Stack.Screen name="checkout" options={{ presentation: "modal" }} />
          <Stack.Screen name="orders" />
          <Stack.Screen name="order/[id]" />
          <Stack.Screen name="notifications" />
          <Stack.Screen name="settings" />
          <Stack.Screen name="support" />
        </Stack>
      </CartProvider>
    </ThemeProvider>
  );
}
