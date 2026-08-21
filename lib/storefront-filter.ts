import type { StoreProduct } from "@/lib/product-api";
import type { StorefrontCircle, StorefrontTab } from "@/lib/storefront-api";

export function isAllStoreTab(tab?: Pick<StorefrontTab, "title">) {
  return tab?.title.trim() === "كل";
}

export function shouldShowStoreProduct(product: StoreProduct, tab?: Pick<StorefrontTab, "title">, circle?: Pick<StorefrontCircle, "title" | "targetCategory">) {
  const productCategories = product.categories?.length ? product.categories : [product.category];
  const tabMatches = !tab || isAllStoreTab(tab) || productCategories.includes(tab.title);
  const circleMatches = !circle || productCategories.includes(circle.targetCategory || circle.title);
  return tabMatches && circleMatches;
}
