import { djangoApi } from "@/lib/django-api";
export async function requestWhatsAppReset(phone:string){return djangoApi<{success:boolean;message:string;whatsapp_url:string}>("/api/auth/password-reset/whatsapp/",{method:"POST",body:JSON.stringify({phone})});}
export async function confirmPasswordReset(token:string,password:string){return djangoApi<{success:boolean;message:string}>(`/api/auth/reset-password/${encodeURIComponent(token)}/`,{method:"POST",body:JSON.stringify({password})});}
