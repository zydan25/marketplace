import { djangoApi } from "@/lib/django-api";

export type OrderStatus = "pending" | "confirmed" | "processing" | "shipped" | "partially_fulfilled" | "delivered" | "cancelled" | "refunded" | "paid_shipping";
export type OrderLinePayload = { productId: number; variantId?: number; color?: string; size?: string; quantity: number };
type DjangoOrder = {
  id: number; order_number: string; status: string; total: string | number; subtotal?: string | number; shipping_fee?: string | number; discount?: string | number;
  shipping_address: Record<string, unknown>; payment_method: string; payment_status: string; currency: string;
  items: Array<{ id: number; product: number; name_snapshot: string; quantity: number; unit_price: string | number; color?: string; size?: string; sku_snapshot?: string; image_url?: string | null }>;
  created_at: string; updated_at?: string;
  timeline?: Array<{ old_status: string; status: string; created_at: string; note?: string }>;
  escrow?: { state: string; held_amount: string; released_amount: string; refunded_amount: string; customer_confirmed: boolean; disputes?: Record<string, { status: string; reason?: string }> } | null;
};

type ChatMessage = { id: number; sender: number; sender_name: string; body: string; attachment_url: string | null; is_read: boolean; created_at: string };
export type OrderChat = { id: number; order: number; vendor_order: number; vendor: number; vendor_name: string; order_number: string; customer: number; subject: string; is_closed: boolean; messages: ChatMessage[] };
export type StoreOrder = {
  id:number; orderCode:string; status:OrderStatus; statusLabel:string; totalAmount:number; subtotal:number; shippingFee:number; discount:number; currency:string; paymentStatus:string; shippingAddress:Record<string,unknown>; createdAt:string;
  items:{id:number;productId:number;productName:string;color:string;size:string;unitPrice:number;quantity:number;sku:string;imageUrl?:string|null}[];
  customer?:{name:string;phone:string;governorate?:string};
  messages?:Array<{id:number;senderRole:"customer"|"admin"|"system";body:string|null;imageUrl:string|null;createdAt?:string}>;
  timeline?:Array<{oldStatus:string;status:string;createdAt:string;note?:string}>;
  escrow?:DjangoOrder["escrow"];
};

function statusLabel(status:string){return({pending:"قيد الانتظار",confirmed:"مؤكد",processing:"قيد التجهيز",shipped:"تم الشحن",partially_fulfilled:"منفذ جزئيًا",delivered:"تم التسليم",cancelled:"ملغي",refunded:"مسترد",paid_shipping:"تم اعتماد الشحن"} as Record<string,string>)[status]||status}
function normalizeOrder(order:DjangoOrder):StoreOrder{return{
  id:order.id,orderCode:order.order_number,status:order.status as OrderStatus,statusLabel:statusLabel(order.status),totalAmount:Number(order.total??0),subtotal:Number(order.subtotal??0),shippingFee:Number(order.shipping_fee??0),discount:Number(order.discount??0),currency:order.currency,paymentStatus:order.payment_status,shippingAddress:order.shipping_address??{},createdAt:order.created_at,
  items:(order.items??[]).map(item=>({id:item.id,productId:item.product,productName:item.name_snapshot,color:item.color??"",size:item.size??"",unitPrice:Number(item.unit_price??0),quantity:item.quantity,sku:item.sku_snapshot??"",imageUrl:item.image_url??null})),
  timeline:(order.timeline??[]).map(item=>({oldStatus:item.old_status,status:item.status,createdAt:item.created_at,note:item.note})),escrow:order.escrow??null,
}}

export async function createOrder(lines:OrderLinePayload[],shippingAddress:Record<string,unknown>={},currency="YER",couponCode=""){const result=await djangoApi<DjangoOrder>("/api/orders/",{method:"POST",body:JSON.stringify({items:lines.map(line=>({product_id:line.productId,variant_id:line.variantId,color:line.color??"",size:line.size??"",quantity:line.quantity})),shipping_address:shippingAddress,payment_method:"wallet",currency,coupon_code:couponCode||undefined})});return normalizeOrder(result)}

export async function getOrder(id:number){return normalizeOrder(await djangoApi<DjangoOrder>(`/api/orders/${id}/order_view/`));}
export async function getMyOrders(){const result=await djangoApi<{results?:DjangoOrder[]}|DjangoOrder[]>("/api/orders/");const items=Array.isArray(result)?result:(result.results??[]);return items.map(normalizeOrder)}
export async function getAdminOrders(){return getMyOrders()}
export async function updateOrderStatus(id:number,status:OrderStatus){return normalizeOrder(await djangoApi<DjangoOrder>(`/api/orders/${id}/update_status/`,{method:"POST",body:JSON.stringify({status:status === "paid_shipping" ? "shipped" : status})}))}
export async function markOrderPaidShipping(id:number){return updateOrderStatus(id,"shipped")}
export async function updatePendingOrder(id:number,payload:{items?:Array<{order_item_id:number;quantity:number}>;shipping_address?:Record<string,unknown>}){return normalizeOrder(await djangoApi<DjangoOrder>(`/api/orders/${id}/update_pending/`,{method:"POST",body:JSON.stringify(payload)}))}
export async function confirmReceived(id:number){return djangoApi<{success:boolean;message:string}>(`/api/orders/${id}/confirm_received/`,{method:"POST",body:JSON.stringify({})})}
export async function rejectOrderItem(id:number,orderItemId:number,reason:string){return djangoApi<{success:boolean;status:string;refund:string}>(`/api/orders/${id}/reject_item/`,{method:"POST",body:JSON.stringify({order_item_id:orderItemId,reason})})}
export async function adminReleaseOrder(id:number){return djangoApi<{success:boolean;released_amount:string;held_amount:string;state:string}>(`/api/orders/${id}/admin_release/`,{method:"POST",body:JSON.stringify({})})}
export async function resolveItemDispute(id:number,orderItemId:number,decision:"refund"|"release"){return djangoApi<{success:boolean;decision:string;status:string}>(`/api/orders/${id}/resolve_item_dispute/`,{method:"POST",body:JSON.stringify({order_item_id:orderItemId,decision})})}

export async function ensureOrderChats(orderId:number){const result=await djangoApi<OrderChat[] | {results?:OrderChat[]}>("/api/order-chats/ensure_for_order/",{method:"POST",body:JSON.stringify({order_id:orderId})});return Array.isArray(result)?result:(result.results??[])}
export async function sendOrderMessage(chatId:number, body:string){const result=await djangoApi<ChatMessage>(`/api/order-chats/${chatId}/send_message/`,{method:"POST",body:JSON.stringify({body})});return result}
export async function markOrderRead(chatId:number){await djangoApi(`/api/order-chats/${chatId}/mark_read/`,{method:"POST",body:JSON.stringify({})})}
