import "./_core/auth";
import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";
import * as Auth from "@/lib/_core/auth";

export type MarketplaceRole = "customer" | "vendor" | "admin";
export type MarketplaceUser = {
  id: number;
  phone: string | null;
  first_name: string;
  middle_name: string;
  third_name: string;
  last_name: string;
  governorate: string;
  role: MarketplaceRole;
  avatar: string | null;
};

const TOKEN_KEY = "django_marketplace_token";
const DEFAULT_DJANGO_API_URL = "https://shopik.alattab.site";

function baseUrl() {
  const explicit = process.env.EXPO_PUBLIC_DJANGO_API_URL?.trim();
  return (explicit || DEFAULT_DJANGO_API_URL).replace(/\/$/, "");
}

async function getToken() {
  const sharedToken = await Auth.getSessionToken();
  if (sharedToken) return sharedToken;
  if (Platform.OS === "web") return typeof localStorage !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null;
  return SecureStore.getItemAsync(TOKEN_KEY);
}

async function saveToken(token: string) {
  await Auth.setSessionToken(token);
  if (Platform.OS === "web") localStorage.setItem(TOKEN_KEY, token);
  else await SecureStore.setItemAsync(TOKEN_KEY, token);
}

export async function djangoApi<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = await getToken();
  const headers = new Headers(init.headers);
  if (!headers.has("Accept")) headers.set("Accept", "application/json");
  if (!headers.has("Content-Type") && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Token ${token}`);

  const response = await fetch(`${baseUrl()}${path.startsWith("/") ? path : `/${path}`}`, { ...init, headers });
  const contentType = response.headers.get("content-type") || "";
  const text = await response.text();
  let data: unknown = null;
  if (text) {
    data = contentType.includes("application/json") ? JSON.parse(text) : { detail: text.slice(0, 300) };
  }
  if (!response.ok) {
    const detail = typeof data === "object" && data !== null && "detail" in data ? String((data as { detail?: unknown }).detail ?? "") : "";
    throw new Error(detail || `تعذر الاتصال بخادم المنصة (${response.status})`);
  }
  return data as T;
}

export async function djangoLogin(phone: string, password: string) {
  const result = await djangoApi<{ token: string; user: MarketplaceUser }>("/api/auth/login/", {
    method: "POST",
    body: JSON.stringify({ phone, password }),
  });
  await saveToken(result.token);
  return result;
}

export async function djangoRegister(input: Record<string, unknown>) {
  const result = await djangoApi<{ token: string; user: MarketplaceUser }>("/api/auth/register/", {
    method: "POST",
    body: JSON.stringify(input),
  });
  await saveToken(result.token);
  return result;
}

export async function djangoLogout() {
  await Auth.removeSessionToken();
  await Auth.clearUserInfo();
  if (Platform.OS === "web") localStorage.removeItem(TOKEN_KEY);
  else await SecureStore.deleteItemAsync(TOKEN_KEY);
}

export function getDjangoTokenKey() {
  return TOKEN_KEY;
}
