import { Stack, type ErrorBoundaryProps } from "expo-router";
import { StatusBar } from "expo-status-bar";
import * as SplashScreen from "expo-splash-screen";
import { I18nManager, Platform, StyleSheet, Text, TouchableOpacity, View } from "react-native";
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

export function ErrorBoundary({ retry }: ErrorBoundaryProps) {
  return (
    <View style={styles.errorRoot}>
      <View style={styles.errorCard}>
        <Text style={styles.errorTitle}>تعذر عرض هذه الصفحة</Text>
        <Text style={styles.errorText}>حدث خطأ مؤقت أثناء تجهيز الشاشة. يمكنك إعادة المحاولة دون فقدان جلسة الدخول.</Text>
        <TouchableOpacity style={styles.retryButton} onPress={() => void retry()}>
          <Text style={styles.retryText}>إعادة المحاولة</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
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

const styles = StyleSheet.create({
  errorRoot: { flex: 1, backgroundColor: "#F7F7F7", justifyContent: "center", alignItems: "center", padding: 24 },
  errorCard: { width: "100%", maxWidth: 420, backgroundColor: "#FFF", borderRadius: 18, padding: 24, alignItems: "center", borderWidth: 1, borderColor: "#E8E8E8" },
  errorTitle: { fontSize: 19, fontWeight: "900", color: "#111", textAlign: "center" },
  errorText: { marginTop: 10, fontSize: 12, lineHeight: 20, color: "#777", textAlign: "center" },
  retryButton: { marginTop: 20, minWidth: 150, height: 46, paddingHorizontal: 22, borderRadius: 23, backgroundColor: "#111", justifyContent: "center", alignItems: "center" },
  retryText: { color: "#FFF", fontSize: 13, fontWeight: "800" },
});
