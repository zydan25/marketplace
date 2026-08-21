import { apiCall } from "@/lib/_core/api";

export type OrderStatus = "pending_payment" | "payment_proof_sent" | "paid_shipping" | "cancelled";
export type StoreOrder = { id: number; orderCode: string; userId: number; status: OrderStatus; statusLabel: string; totalAmount: number; createdAt: string; customer?: { name: string; phone: string; governorate: string }; items: { id: number; productId: number; productName: string; imageUrl: string | null; color: string; size: string; unitPrice: number; quantity: number }[]; messages: { id: number; senderRole: "customer" | "admin" | "system"; body: string | null; imageUrl: string | null; createdAt: string }[] };
export type OrderLinePayload = { productId: number; color: string; size: string; quantity: number };
export async function createOrder(lines: OrderLinePayload[]) { return (await apiCall<{ order: StoreOrder }>("/api/orders", { method: "POST", body: JSON.stringify({ lines }) })).order; }
export async function getOrder(id: number) { return (await apiCall<{ order: StoreOrder }>(`/api/orders/${id}`)).order; }
export async function getMyOrders() { return (await apiCall<{ orders: StoreOrder[] }>("/api/orders")).orders; }
export async function sendOrderMessage(id: number, body: string, imageDataUrl?: string) { return (await apiCall<{ order: StoreOrder }>(`/api/orders/${id}/messages`, { method: "POST", body: JSON.stringify({ body, imageDataUrl }) })).order; }
export async function getAdminOrders() { return (await apiCall<{ orders: StoreOrder[] }>("/api/admin/orders")).orders; }
export async function markOrderPaidShipping(id: number) { return (await apiCall<{ order: StoreOrder }>(`/api/admin/orders/${id}/paid-shipping`, { method: "PATCH", body: JSON.stringify({}) })).order; }
