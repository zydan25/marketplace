import "./scripts/load-env.js";
import type { ExpoConfig } from "expo/config";

const variant = process.env.APP_VARIANT === "vendor" ? "vendor" : "customer";
const basePackage = "com.app.truediscountfashion";
const rawBundleId = variant === "vendor" ? `${basePackage}.vendor` : basePackage;
const bundleId = rawBundleId
  .replace(/[-_]/g, ".")
  .replace(/[^a-zA-Z0-9.]/g, "")
  .replace(/\.+/g, ".")
  .replace(/^\.+|\.+$/g, "")
  .toLowerCase()
  .split(".")
  .map((segment) => (/^[a-zA-Z]/.test(segment) ? segment : `x${segment}`))
  .join(".") || "com.app.truediscountfashion";
const timestamp = bundleId.split(".").pop()?.replace(/^t/, "") ?? "";
const schemeFromBundleId = `manus${timestamp}`;

const appName = variant === "vendor" ? "شبيك — التاجر" : "شبيك";
const appSlug = "shabik-marketplace";
const easProjectId = process.env.EAS_PROJECT_ID?.trim();

const config: ExpoConfig = {
  name: appName,
  slug: appSlug,
  owner: "zydan2626",
  version: "1.0.0",
  orientation: "portrait",
  icon: "./assets/images/icon.png",
  scheme: schemeFromBundleId,
  userInterfaceStyle: "light",
  newArchEnabled: true,
  extra: {
    appVariant: variant,
    djangoApiUrl: process.env.EXPO_PUBLIC_DJANGO_API_URL ?? "",
    ...(easProjectId ? { eas: { projectId: easProjectId } } : {}),
  },
  ios: {
    supportsTablet: true,
    bundleIdentifier: bundleId,
    infoPlist: { ITSAppUsesNonExemptEncryption: false },
  },
  android: {
    adaptiveIcon: {
      backgroundColor: "#FFFFFF",
      foregroundImage: "./assets/images/android-icon-foreground.png",
      backgroundImage: "./assets/images/android-icon-background.png",
      monochromeImage: "./assets/images/android-icon-monochrome.png",
    },
    edgeToEdgeEnabled: true,
    predictiveBackGestureEnabled: false,
    package: bundleId,
    permissions: ["POST_NOTIFICATIONS"],
    intentFilters: [{ action: "VIEW", autoVerify: true, data: [{ scheme: schemeFromBundleId, host: "*" }], category: ["BROWSABLE", "DEFAULT"] }],
  },
  web: { bundler: "metro", output: "static", favicon: "./assets/images/favicon.png" },
  plugins: [
    "expo-router",
    ["expo-image-picker", { photosPermission: "السماح للتطبيق بالوصول إلى الصور لإضافة صور الأصناف." }],
    ["expo-audio", { microphonePermission: "السماح للتطبيق باستخدام الميكروفون." }],
    ["expo-video", { supportsBackgroundPlayback: true, supportsPictureInPicture: true }],
    ["expo-splash-screen", { image: "./assets/images/splash-icon.png", imageWidth: 200, resizeMode: "contain", backgroundColor: "#FFFFFF" }],
    ["expo-build-properties", { android: { buildArchs: ["armeabi-v7a", "arm64-v8a"], minSdkVersion: 24 } }],
  ],
  experiments: { typedRoutes: true, reactCompiler: true },
};

export default config;
