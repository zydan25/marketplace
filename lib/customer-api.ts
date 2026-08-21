import { apiCall } from "@/lib/_core/api";

export type CustomerSummary = { id: number; name: string; phone: string; governorate: string; createdAt: string; rewardCount: number };
export type CustomerReward = { id: number; rewardType: "gift" | "coupon" | "order_threshold" | "quantity_threshold"; title: string; couponCode: string | null; discountType: "fixed" | "percent"; discountValue: number; minimumOrderAmount: number; minimumQuantity: number; giftName: string | null; isActive: boolean; expiresAt: string | null; createdAt: string };
export type CustomerProfile = CustomerSummary & { rewards: CustomerReward[] };
export type CustomerRewardPayload = { rewardType: CustomerReward["rewardType"]; title: string; couponCode?: string; discountType: CustomerReward["discountType"]; discountValue: number; minimumOrderAmount: number; minimumQuantity: number; giftName?: string; isActive: boolean };
export async function getAdminCustomers() { return (await apiCall<{ customers: CustomerSummary[] }>("/api/admin/customers")).customers; }
export async function getAdminCustomer(id: number) { return (await apiCall<{ customer: CustomerProfile }>(`/api/admin/customers/${id}`)).customer; }
export async function assignCustomerReward(id: number, payload: CustomerRewardPayload) { return (await apiCall<{ reward: CustomerReward }>(`/api/admin/customers/${id}/rewards`, { method: "POST", body: JSON.stringify(payload) })).reward; }
export async function setCustomerRewardActive(id: number, isActive: boolean) { return apiCall<{ ok: boolean }>(`/api/admin/rewards/${id}`, { method: "PATCH", body: JSON.stringify({ isActive }) }); }
export async function validateMyCoupon(code: string, orderAmount: number, quantity: number) { return (await apiCall<{ reward: { id: number; title: string; couponCode: string; discount: number } }>("/api/customer/rewards/validate", { method: "POST", body: JSON.stringify({ code, orderAmount, quantity }) })).reward; }
