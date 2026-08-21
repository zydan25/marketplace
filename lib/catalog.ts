import type { StoreProduct } from "./product-api";

export type Product = StoreProduct;

// لا توجد منتجات جاهزة: يمتلئ المتجر فقط بالأصناف المنشورة من لوحة المدير.
export const products: Product[] = [];
export const storeTabs = ["الكل", "وصل حديثًا", "الأكثر مبيعًا", "عروض اليوم"];
export const categories = [
  { id: "all", title: "الكل", emoji: "✦" },
  { id: "women", title: "نسائي", emoji: "◒" },
  { id: "kids", title: "أطفال", emoji: "◐" },
  { id: "new", title: "وصل حديثًا", emoji: "✚" },
];

export function findProduct(id?: string) { return products.find((product) => product.id === id); }
export function formatYER(value: number) { return `${new Intl.NumberFormat("ar-YE").format(value)} ر.ي`; }
