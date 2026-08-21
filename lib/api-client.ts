import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";
import { API_BASE_URL } from "@/constants/oauth";
import * as Auth from "@/lib/_core/auth";

const TOKEN_KEY = "django_marketplace_token";

function getBaseUrl() {
  const explicit = process.env.EXPO_PUBLIC_DJANGO_API_URL;
  if (explicit) return explicit.replace(/\/$/, "");
  if (Platform.OS === "web" && typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    // إذا كان يعمل على الويب التجريبي عبر منفذ 8081 أو 8082، وجهه إلى منفذ 8000
    if (hostname.startsWith("8081-") || hostname.startsWith("8082-")) {
      const apiHostname = hostname.replace(/^808[12]-/, "8000-");
      return `${protocol}//${apiHostname}`;
    }
    return window.location.origin;
  }
  return "https://shopik.alattab.site";
}

async function getToken() {
  const sharedToken = await Auth.getSessionToken();
  if (sharedToken) return sharedToken;
  if (Platform.OS === "web") {
    return typeof localStorage !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null;
  }
  return SecureStore.getItemAsync(TOKEN_KEY);
}

export async function saveToken(token: string) {
  await Auth.setSessionToken(token);
  if (Platform.OS === "web") {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    await SecureStore.setItemAsync(TOKEN_KEY, token);
  }
}

export async function removeToken() {
  await Auth.removeSessionToken();
  if (Platform.OS === "web") {
    localStorage.removeItem(TOKEN_KEY);
  } else {
    await SecureStore.deleteItemAsync(TOKEN_KEY);
  }
}

export class ApiClient {
  static async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = await getToken();
    const headers = new Headers(options.headers);

    if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
      headers.set("Content-Type", "application/json");
    }

    if (token) {
      headers.set("Authorization", `Token ${token}`);
    }

    const url = `${getBaseUrl()}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;

    try {
      const response = await fetch(url, { ...options, headers });
      const text = await response.text();
      const data = text ? JSON.parse(text) : null;

      if (!response.ok) {
        if (response.status === 401) {
          // Token expired or invalid
          await removeToken();
          // Here we would trigger a logout event or navigation to login
        }

        throw {
          status: response.status,
          message: data?.detail || data?.message || "حدث خطأ في الاتصال بالخادم",
          errors: data?.errors || data,
        };
      }

      return data as T;
    } catch (error: any) {
      if (error.status) throw error;
      throw { status: 0, message: error.message || "تعذر الاتصال بالخادم", errors: null };
    }
  }

  static get<T>(endpoint: string, options?: RequestInit) {
    return this.request<T>(endpoint, { ...options, method: "GET" });
  }

  static post<T>(endpoint: string, body: any, options?: RequestInit) {
    return this.request<T>(endpoint, { ...options, method: "POST", body: JSON.stringify(body) });
  }

  static patch<T>(endpoint: string, body: any, options?: RequestInit) {
    return this.request<T>(endpoint, { ...options, method: "PATCH", body: JSON.stringify(body) });
  }

  static delete<T>(endpoint: string, options?: RequestInit) {
    return this.request<T>(endpoint, { ...options, method: "DELETE" });
  }
}
