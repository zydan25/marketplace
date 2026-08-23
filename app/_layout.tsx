import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import * as SplashScreen from "expo-splash-screen";
import { I18nManager, Platform } from "react-native";
import { useCallback, useEffect, useState } from "react";
import { initialWindowMetrics, SafeAreaProvider } from "react-native-safe-area-context";

import { WelcomeScreen } from "@/components/welcome-screen";
import { CartProvider } from "@/lib/cart-context";
import { ThemeProvider } from "@/lib/theme-provider";

I18nManager.allowRTL(true);

SplashScreen.preventAutoHideAsync();
SplashScreen.setOptions({ duration: 450, fade: true });

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
  const [welcomeVisible, setWelcomeVisible] = useState(true);

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      SplashScreen.hideAsync().catch(() => undefined);
    });
    return () => cancelAnimationFrame(frame);
  }, []);

  const finishWelcome = useCallback(() => setWelcomeVisible(false), []);

  return (
    <SafeAreaProvider initialMetrics={initialWindowMetrics}>
      <ThemeProvider>
        <CartProvider>
          <DocumentDirection />
          <StatusBar style="dark" />
          <Stack screenOptions={{ headerShown: false, animation: "slide_from_left" }}>
            <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
            <Stack.Screen name="login" options={{ presentation: "fullScreenModal" }} />
            <Stack.Screen name="register" options={{ presentation: "fullScreenModal" }} />
            <Stack.Screen name="admin/index" />
            <Stack.Screen name="admin/products" />
            <Stack.Screen name="admin/storefront" />
            <Stack.Screen name="product/[id]" />
            <Stack.Screen name="search" />
            <Stack.Screen name="checkout" options={{ presentation: "fullScreenModal" }} />
            <Stack.Screen name="orders" />
            <Stack.Screen name="order/[id]" />
            <Stack.Screen name="notifications" />
            <Stack.Screen name="settings" />
            <Stack.Screen name="support" />
          </Stack>
          {welcomeVisible ? <WelcomeScreen onFinished={finishWelcome} /> : null}
        </CartProvider>
      </ThemeProvider>
    </SafeAreaProvider>
  );
}
