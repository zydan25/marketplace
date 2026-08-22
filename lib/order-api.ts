import { djangoApi } from "@/lib/django-api";

export type OrderStatus = "pending" | "confirmed" | "processing" | "shipped" | "partially_fulfilled" | "delivered" | "cancelled" | "refunded";
export type OrderLinePayload = { productId: number; variantId?: number; color?: string; size?: string; quantity: number };
type DjangoOrder = { id: number; order_number: string; status: string; total: string | number; shipping_address: Record<string, unknown>; payment_method: string; payment_status: string; currency: string; items: Array<{ id: number; product: number; name_snapshot: string; quantity: number; unit_price: string | number; color?: string; size?: string; sku_snapshot?: string }>; created_at: string; updated_at?: string };

export type StoreOrder = { id:number;orderCode:string;status:OrderStatus;statusLabel:string;totalAmount:number;createdAt:string;items:{id:number;productId:number;productName:string;color:string;size:string;unitPrice:number;quantity:number;sku:string}[] };

function statusLabel(status:string){return({pending:"قيد الانتظار",confirmed:"مؤكد",processing:"قيد التجهيز",shipped:"تم الشحن",partially_fulfilled:"منفذ جزئيًا",delivered:"تم التسليم",cancelled:"ملغي",refunded:"مسترد"} as Record<string,string>)[status]||status}
function normalizeOrder(order:DjangoOrder):StoreOrder{return{id:order.id,orderCode:order.order_number,status:order.status as OrderStatus,statusLabel:statusLabel(order.status),totalAmount:Number(order.total??0),createdAt:order.created_at,items:(order.items??[]).map(item=>({id:item.id,productId:item.product,productName:item.name_snapshot,color:item.color??"",size:item.size??"",unitPrice:Number(item.unit_price??0),quantity:item.quantity,sku:item.sku_snapshot??""}))}}

export async function createOrder(lines:OrderLinePayload[],shippingAddress:Record<string,unknown>={},currency="YER",couponCode=""){const result=await djangoApi<DjangoOrder>("/api/orders/",{method:"POST",body:JSON.stringify({items:lines.map(line=>({product_id:line.productId,variant_id:line.variantId,color:line.color??"",size:line.size??"",quantity:line.quantity})),shipping_address:shippingAddress,payment_method:"cash_on_delivery",currency,coupon_code:couponCode||undefined})});return normalizeOrder(result)}
export async function getOrder(id:number){return normalizeOrder(await djangoApi<DjangoOrder>(`/api/orders/${id}/`))}
export async function getMyOrders(){const result=await djangoApi<{results?:DjangoOrder[]}|DjangoOrder[]>("/api/orders/");const items=Array.isArray(result)?result:(result.results??[]);return items.map(normalizeOrder)}
export async function updateOrderStatus(id:number,status:OrderStatus){return normalizeOrder(await djangoApi<DjangoOrder>(`/api/orders/${id}/update_status/`,{method:"POST",body:JSON.stringify({status})}))}
