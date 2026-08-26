import { djangoApi } from "@/lib/django-api";
export type ProductComment={id:number;product:number;user:number;user_name:string;body:string;parent:number|null;created_at:string;updated_at:string};
export async function toggleFavorite(product:number){return djangoApi<{favorite:boolean}>("/api/favorites/toggle/",{method:"POST",body:JSON.stringify({product})});}
export async function getFavoriteForProduct(product:number){const data=await djangoApi<{results?:{product:number}[]}|{product:number}[]>(`/api/favorites/?product=${product}`);const rows=Array.isArray(data)?data:data.results??[];return rows.some(item=>item.product===product);}
export async function getProductComments(product:number){const data=await djangoApi<{results?:ProductComment[]}|ProductComment[]>(`/api/product-comments/?product=${product}`);return Array.isArray(data)?data:data.results??[];}
export async function addProductComment(product:number,body:string,parent?:number){return djangoApi<ProductComment>("/api/product-comments/",{method:"POST",body:JSON.stringify({product,body,parent:parent??null})});}
