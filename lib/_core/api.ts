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
  role: "user" | "admin" | "vendor" | "customer";
  lastSignedIn: string;
};

export type PhoneAuthResult = { sessionToken: string; user: PhoneAuthUser };

type DjangoUser = {
  id: number;
  phone: string | null;
  email: string | null;
  first_name?: string;
  middle_name?: string;
  third_name?: string;
  last_name?: string;
  governorate?: string | null;
  role?: PhoneAuthUser["role"];
  avatar?: string | null;
};

type DjangoAuthResponse = { token: string; user: DjangoUser };

function baseUrl() {
  const explicit = process.env.EXPO_PUBLIC_DJANGO_API_URL;
  return (explicit || getApiBaseUrl()).replace(/\/$/, "");
}

function mapUser(user: DjangoUser): PhoneAuthUser {
  const name = [user.first_name, user.middle_name, user.third_name, user.last_name]
    .filter(Boolean)
    .join(" ") || user.phone || "مستخدم";
  return {
    id: user.id,
    openId: String(user.id),
    name,
    email: user.email || null,
    phone: user.phone || null,
    governorate: user.governorate || null,
    loginMethod: "phone",
    role: user.role || "customer",
    lastSignedIn: new Date().toISOString(),
  };
}

export async function apiCall<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json", ...((options.headers as Record<string, string>) || {}) };
  const token = await Auth.getSessionToken();
  if (token) headers.Authorization = `Token ${token}`;
  const prefix = baseUrl();
  const url = `${prefix}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
  const response = await fetch(url, { ...options, headers });
  const text = await response.text();
  let data: unknown = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!response.ok) {
    const payload = data as { detail?: string; message?: string } | null;
    throw new Error(payload?.detail || payload?.message || `تعذر تنفيذ الطلب (${response.status}).`);
  }
  return data as T;
}

export async function exchangeOAuthCode(code: string, state: string): Promise<PhoneAuthResult> {
  const params = new URLSearchParams({ code, state });
  const result = await apiCall<{ token: string; user: DjangoUser }>(`/api/auth/oauth/?${params.toString()}`);
  return { sessionToken: result.token, user: mapUser(result.user) };
}

export async function loginWithPhone(phone: string, password: string): Promise<PhoneAuthResult> {
  const result = await apiCall<DjangoAuthResponse>("/api/auth/login/", { method: "POST", body: JSON.stringify({ phone, password }) });
  return { sessionToken: result.token, user: mapUser(result.user) };
}

export async function registerWithPhone(input: { firstName: string; secondName: string; thirdName: string; familyName: string; phone: string; password: string; governorate: string; referralCode?: string }): Promise<PhoneAuthResult> {
  const result = await apiCall<DjangoAuthResponse>("/api/auth/register/", {
    method: "POST",
    body: JSON.stringify({
      phone: input.phone,
      password: input.password,
      first_name: input.firstName,
      middle_name: input.secondName,
      third_name: input.thirdName,
      last_name: input.familyName,
      governorate: input.governorate,
      referral_code: input.referralCode,
    }),
  });
  return { sessionToken: result.token, user: mapUser(result.user) };
}

export async function logout(): Promise<void> {
  await Auth.removeSessionToken();
}

export async function getMe(): Promise<PhoneAuthUser | null> {
  try {
    const result = await apiCall<DjangoUser>("/api/auth/me/");
    return mapUser(result);
  } catch {
    return null;
  }
}

export async function establishSession(token: string): Promise<boolean> {
  try {
    const response = await fetch(`${baseUrl()}/api/auth/me/`, { headers: { Authorization: `Token ${token}` } });
    return response.ok;
  } catch {
    return false;
  }
}
