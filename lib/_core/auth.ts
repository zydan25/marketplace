import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";
import { SESSION_TOKEN_KEY, USER_INFO_KEY } from "@/constants/oauth";

export type User = {
  id: number;
  openId: string;
  name: string | null;
  email: string | null;
  phone?: string | null;
  governorate?: string | null;
  loginMethod: string | null;
  role?: "user" | "admin" | "vendor" | "customer";
  points_balance?: number;
  lastSignedIn: Date;
};

let webTokenFallback: string | null = null;
let webUserFallback: User | null = null;

function canUseWebStorage() {
  return Platform.OS === "web" && typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export async function getSessionToken(): Promise<string | null> {
  try {
    if (canUseWebStorage()) {
      try { return window.localStorage.getItem(SESSION_TOKEN_KEY) || webTokenFallback; }
      catch { return webTokenFallback; }
    }
    return await SecureStore.getItemAsync(SESSION_TOKEN_KEY);
  } catch (error) {
    console.error("[Auth] Failed to get session token:", error);
    return null;
  }
}

export async function setSessionToken(token: string): Promise<void> {
  if (!token) throw new Error("جلسة الدخول غير صالحة.");
  if (canUseWebStorage()) {
    webTokenFallback = token;
    try { window.localStorage.setItem(SESSION_TOKEN_KEY, token); } catch { /* memory fallback keeps current tab authenticated */ }
    return;
  }
  await SecureStore.setItemAsync(SESSION_TOKEN_KEY, token);
}

export async function removeSessionToken(): Promise<void> {
  webTokenFallback = null;
  try {
    if (canUseWebStorage()) {
      try { window.localStorage.removeItem(SESSION_TOKEN_KEY); } catch { /* ignore */ }
      return;
    }
    await SecureStore.deleteItemAsync(SESSION_TOKEN_KEY);
  } catch (error) {
    console.error("[Auth] Failed to remove session token:", error);
  }
}

export async function getUserInfo(): Promise<User | null> {
  try {
    if (canUseWebStorage()) {
      try {
        const info = window.localStorage.getItem(USER_INFO_KEY);
        if (info) return JSON.parse(info) as User;
      } catch { /* fall back to in-memory identity */ }
      return webUserFallback;
    }
    const info = await SecureStore.getItemAsync(USER_INFO_KEY);
    return info ? JSON.parse(info) as User : null;
  } catch (error) {
    console.error("[Auth] Failed to get user info:", error);
    return null;
  }
}

export async function setUserInfo(user: User): Promise<void> {
  webUserFallback = user;
  if (canUseWebStorage()) {
    try { window.localStorage.setItem(USER_INFO_KEY, JSON.stringify(user)); } catch { /* memory fallback */ }
    return;
  }
  await SecureStore.setItemAsync(USER_INFO_KEY, JSON.stringify(user));
}

export async function clearUserInfo(): Promise<void> {
  webUserFallback = null;
  try {
    if (canUseWebStorage()) {
      try { window.localStorage.removeItem(USER_INFO_KEY); } catch { /* ignore */ }
      return;
    }
    await SecureStore.deleteItemAsync(USER_INFO_KEY);
  } catch (error) {
    console.error("[Auth] Failed to clear user info:", error);
  }
}
