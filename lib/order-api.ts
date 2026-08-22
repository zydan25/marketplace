import { apiCall } from "@/lib/_core/api";

export type OrderStatus = "pending_payment" | "payment_proof_sent" | "paid_shipping" | "cancelled";
export type StoreOrder = { id: number; orderCode: string; userId: number; status: OrderStatus; statusLabel: string; totalAmount: number; createdAt: string; customer?: { name: string; phone: string; governorate: string }; items: { id: number; productId: number; productName: string; imageUrl: string | null; color: string; size: string; unitPrice: number; quantity: number }[]; messages: { id: number; senderRole: "customer" | "admin" | "system"; body: string | null; imageUrl: string | null; createdAt: string }[] };
export type OrderLinePayload = { productId: number; color: string; size: string; quantity: number };
type DjangoOrder = { id: number; order_number: string; status: string; subtotal: string | number; shipping_fee: string | number; discount: string | number; total: string | number; currency: string; shipping_address: Record<string, unknown>; payment_method: string; payment_status: string; items: Array<{ id: number; product: number; name_snapshot: string; quantity: number; unit_price: string | number; color?: string; size?: string }>; created_at: string };

function normalizeOrder(order: DjangoOrder): StoreOrder {
  return {
    id: order.id,
    orderCode: order.order_number,
    userId: 0,
    status: order.status as OrderStatus,
    statusLabel: order.status,
    totalAmount: Number(order.total ?? 0),
    createdAt: order.created_at,
    customer: undefined,
    items: (order.items ?? []).map((item) => ({ id: item.id, productId: item.product, productName: item.name_snapshot, imageUrl: null, color: item.color ?? "", size: item.size ?? "", unitPrice: Number(item.unit_price ?? 0), quantity: item.quantity })),
    messages: [],
  };
}

export async function createOrder(lines: OrderLinePayload[], shippingAddress: Record<string, unknown> = {}) {
  const result = await apiCall<DjangoOrder>("/api/orders/", { method: "POST", body: JSON.stringify({ items: lines.map((line) => ({ product_id: line.productId, color: line.color, size: line.size, quantity: line.quantity })), shipping_address: shippingAddress, payment_method: "cash_on_delivery", currency: "YER" }) });
  return normalizeOrder(result);
}
export async function getOrder(id: number) { return normalizeOrder(await apiCall<DjangoOrder>(`/api/orders/${id}/`)); }
export async function getMyOrders() { const result = await apiCall<{ results?: DjangoOrder[] } | DjangoOrder[]>("/api/orders/"); const items = Array.isArray(result) ? result : (result.results ?? []); return items.map(normalizeOrder); }
export async function sendOrderMessage(id: number, body: string, imageDataUrl?: string) { return (await apiCall<{ order: StoreOrder }>(`/api/orders/${id}/messages`, { method: "POST", body: JSON.stringify({ body, imageDataUrl }) })).order; }
export async function getAdminOrders() { return getMyOrders(); }
export async function markOrderPaidShipping(id: number) { return (await apiCall<{ order: StoreOrder }>(`/api/admin/orders/${id}/paid-shipping`, { method: "PATCH", body: JSON.stringify({}) })).order; }
