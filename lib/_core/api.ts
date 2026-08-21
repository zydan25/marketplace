import { Platform } from "react-native";

import { getApiBaseUrl } from "@/constants/oauth";
import * as Auth from "./auth";

export type PhoneAuthUser = {
  id: number;
  openId: string;
  name: string | null;
  email: string | null;
  phone: string | null;
  governorate: string | null;
  loginMethod: string | null;
  role: "user" | "admin";
  lastSignedIn: string;
};

export type PhoneAuthResult = { sessionToken: string; user: PhoneAuthUser };

export async function apiCall<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json", ...((options.headers as Record<string, string>) || {}) };
  const token = await Auth.getSessionToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const baseUrl = getApiBaseUrl();
  const url = baseUrl ? `${baseUrl.replace(/\/$/, "")}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}` : endpoint;
  const response = await fetch(url, { ...options, headers, credentials: "include" });
  if (!response.ok) {
    const text = await response.text();
    try { throw new Error(JSON.parse(text).error || text); } catch (error) { if (error instanceof Error) throw error; throw new Error(text || "تعذر تنفيذ الطلب."); }
  }
  return response.json() as Promise<T>;
}

export async function exchangeOAuthCode(code: string, state: string): Promise<{ sessionToken: string; user: PhoneAuthUser }> {
  const params = new URLSearchParams({ code, state });
  const result = await apiCall<{ app_session_id: string; user: PhoneAuthUser }>(`/api/oauth/mobile?${params.toString()}`);
  return { sessionToken: result.app_session_id, user: result.user };
}

export async function loginWithPhone(phone: string, password: string): Promise<PhoneAuthResult> {
  return apiCall<PhoneAuthResult>("/api/phone-auth/login", { method: "POST", body: JSON.stringify({ phone, password }) });
}

export async function registerWithPhone(input: { firstName: string; secondName: string; thirdName: string; familyName: string; phone: string; password: string; governorate: string; referralCode?: string }): Promise<PhoneAuthResult> {
  return apiCall<PhoneAuthResult>("/api/phone-auth/register", { method: "POST", body: JSON.stringify(input) });
}

export async function logout(): Promise<void> {
  await apiCall<void>("/api/auth/logout", { method: "POST" });
}

export async function getMe(): Promise<PhoneAuthUser | null> {
  try {
    const result = await apiCall<{ user: PhoneAuthUser }>("/api/auth/me");
    return result.user || null;
  } catch {
    return null;
  }
}

export async function establishSession(token: string): Promise<boolean> {
  try {
    const url = `${getApiBaseUrl()}/api/auth/session`;
    const response = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, credentials: "include" });
    return response.ok;
  } catch {
    return false;
  }
}
