import { useEffect, useState } from "react";
import { ApiClient } from "@/lib/api-client";
import { djangoApi } from "@/lib/django-api";
import { apiCall } from "@/lib/_core/api";

/* ─── Types ──────────────────────────────────────── */

export interface DashboardStats {
  users: number;
  customers: number;
  vendors: number;
  pending_vendors: number;
  products: number;
  orders: number;
  pending_orders: number;
  wallets: number;
}

export interface Order {
  id: number;
  order_number: string;
  status: string;
  total: string | number;
  subtotal: string | number;
  shipping_fee: string | number;
  discount: string | number;
  payment_status: string;
  payment_method: string;
  currency: string;
  created_at: string;
  updated_at: string;
  customer?: { id: number; name?: string; phone?: string; first_name?: string; last_name?: string };
  items?: OrderItem[];
  vendor_orders?: VendorOrder[];
}

export interface OrderItem {
  id: number;
  product?: number;
  name_snapshot?: string;
  sku_snapshot?: string;
  quantity: number;
  unit_price: string | number;
  vendor_total?: string | number;
  commission?: string | number;
}

export interface VendorOrder {
  id: number;
  status: string;
  subtotal: string | number;
  total: string | number;
  commission: string | number;
  vendor_net: string | number;
}

export interface Product {
  id: number;
  name: string;
  sku: string;
  price: string | number;
  sale_price?: string | number;
  effective_price?: string | number;
  stock: number;
  sold_count: number;
  rating: string | number;
  reviews_count: number;
  is_published: boolean;
  is_trending: boolean;
  vendor?: { id: number; store_name?: string };
  categories?: { id: number; name?: string }[];
  main_image_url?: string;
}

export interface Customer {
  id: number;
  name: string;
  phone: string;
  role: string;
  is_active: boolean;
  points_balance?: number;
  order_count?: number;
  total_spent?: number;
  governorate?: string;
}

export interface Wallet {
  id: number;
  user?: { id: number; name?: string; phone?: string };
  balance: string | number;
  currency: string;
  is_locked: boolean;
  transactions?: WalletTransaction[];
}

export interface WalletTransaction {
  id: number;
  transaction_type: string;
  amount: string | number;
  balance_after: string | number;
  reference: string;
  note: string;
  created_at: string;
}

export interface VendorProfile {
  id: number;
  store_name: string;
  slug: string;
  status: string;
  commission_percent: string | number;
  owner?: { id: number; name?: string; phone?: string };
}

export interface Conversation {
  id: number;
  subject: string;
  is_closed: boolean;
  customer?: { id: number; name?: string };
  vendor?: { id: number; store_name?: string };
  messages?: { id: number; body: string; sender?: { id: number }; is_read: boolean; created_at: string }[];
  created_at: string;
}

export interface Coupon {
  id: number;
  code: string;
  discount_percent: string | number;
  discount_amount: string | number;
  usage_limit?: number;
  used_count: number;
  is_active: boolean;
}

export interface Referral {
  id: number;
  inviter_name?: string;
  invitee_name?: string;
  code: string;
  reward_amount: string | number;
  reward_paid: boolean;
  created_at: string;
}

/* ─── Hooks ──────────────────────────────────────── */

export function useDashboardStats() {
  const [data, setData] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        setLoading(true);
        const res = await ApiClient.get<DashboardStats>("/api/admin-dashboard/");
        if (mounted) { setData(res); setError(null); }
      } catch (e: any) {
        if (mounted) setError(e?.message || "خطأ في تحميل البيانات");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, []);

  return { data, loading, error };
}

export function useOrders(limit?: number) {
  const [data, setData] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        setLoading(true);
        const res = await djangoApi<Order[] | { results?: Order[] }>("/api/orders/");
        const items = Array.isArray(res) ? res : (res.results ?? []);
        const sorted = [...items].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        if (mounted) { setData(limit ? sorted.slice(0, limit) : sorted); setError(null); }
      } catch (e: any) {
        if (mounted) setError(e?.message || "خطأ في تحميل الطلبات");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, [limit]);

  return { data, loading, error };
}

export function useProducts() {
  const [data, setData] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        setLoading(true);
        const res = await djangoApi<Product[] | { results?: Product[] }>("/api/products/");
        const items = Array.isArray(res) ? res : (res.results ?? []);
        if (mounted) { setData(items); setError(null); }
      } catch (e: any) {
        if (mounted) setError(e?.message || "خطأ في تحميل المنتجات");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, []);

  return { data, loading, error };
}

export function useCustomers() {
  const [data, setData] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        setLoading(true);
        const res = await apiCall<{ customers: Customer[] }>("/api/admin/customers");
        if (mounted) { setData(res.customers || []); setError(null); }
      } catch (e: any) {
        if (mounted) setError(e?.message || "خطأ في تحميل العملاء");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, []);

  return { data, loading, error };
}

export function useWallets() {
  const [data, setData] = useState<Wallet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        setLoading(true);
        const res = await ApiClient.get<{ results?: Wallet[] }>("/api/wallets/");
        if (mounted) { setData(res.results ?? []); setError(null); }
      } catch (e: any) {
        if (mounted) setError(e?.message || "خطأ في تحميل المحافظ");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, []);

  return { data, loading, error };
}

export function useVendors() {
  const [data, setData] = useState<VendorProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        setLoading(true);
        const res = await djangoApi<VendorProfile[] | { results?: VendorProfile[] }>("/api/vendors/");
        const items = Array.isArray(res) ? res : (res.results ?? []);
        if (mounted) { setData(items); setError(null); }
      } catch (e: any) {
        if (mounted) setError(e?.message || "خطأ في تحميل البائعين");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, []);

  return { data, loading, error };
}

export function useConversations() {
  const [data, setData] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        setLoading(true);
        const res = await djangoApi<Conversation[] | { results?: Conversation[] }>("/api/conversations/");
        const items = Array.isArray(res) ? res : (res.results ?? []);
        if (mounted) { setData(items); setError(null); }
      } catch (e: any) {
        if (mounted) setError(e?.message || "خطأ في تحميل المحادثات");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, []);

  return { data, loading, error };
}

export function useCoupons() {
  const [data, setData] = useState<Coupon[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        setLoading(true);
        const res = await djangoApi<Coupon[] | { results?: Coupon[] }>("/api/coupons/");
        const items = Array.isArray(res) ? res : (res.results ?? []);
        if (mounted) { setData(items); setError(null); }
      } catch (e: any) {
        if (mounted) setError(e?.message || "خطأ في تحميل الكوبونات");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, []);

  return { data, loading, error };
}

/* ─── Analytics Helpers ──────────────────────────── */

export function countByStatus<T extends { status: string }>(items: T[]): Record<string, number> {
  const result: Record<string, number> = {};
  for (const item of items) {
    result[item.status] = (result[item.status] || 0) + 1;
  }
  return result;
}

export function groupBy<T>(items: T[], key: keyof T): Record<string, T[]> {
  const result: Record<string, T[]> = {};
  for (const item of items) {
    const val = String(item[key] ?? "غير معروف");
    if (!result[val]) result[val] = [];
    result[val].push(item);
  }
  return result;
}

export function sumValues(items: Record<string, number>): number {
  return Object.values(items).reduce((a, b) => a + b, 0);
}

export function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, "0")}/${String(d.getDate()).padStart(2, "0")}`;
}

export function formatDateTime(dateStr: string): string {
  const d = new Date(dateStr);
  return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, "0")}/${String(d.getDate()).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export function toNumber(v: string | number | undefined): number {
  if (v === undefined || v === null) return 0;
  return typeof v === "string" ? parseFloat(v) || 0 : v;
}

export function sumField<T>(items: T[], field: keyof T): number {
  return items.reduce((acc, item) => acc + toNumber(item[field] as string | number), 0);
}

export function getTopN(items: { label: string; value: number }[], n = 10): { label: string; value: number }[] {
  return [...items].sort((a, b) => b.value - a.value).slice(0, n);
}

export function filterByDateRange(items: { created_at: string }[], from?: string, to?: string): typeof items {
  return items.filter((item) => {
    const d = new Date(item.created_at);
    if (from && d < new Date(from)) return false;
    if (to) {
      const toDate = new Date(to);
      toDate.setHours(23, 59, 59, 999);
      if (d > toDate) return false;
    }
    return true;
  });
}

export function getGovernorateCounts(items: { governorate?: string }[]): Record<string, number> {
  return items.reduce((acc, item) => {
    const g = item.governorate || "غير محدد";
    acc[g] = (acc[g] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
}
