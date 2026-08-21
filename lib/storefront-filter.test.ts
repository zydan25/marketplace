import { describe, expect, it } from "vitest";

import type { StoreProduct } from "@/lib/product-api";
import { shouldShowStoreProduct } from "./storefront-filter";

const product = { id: "1", category: "أطفال", categories: ["أطفال", "بناتي"] } as StoreProduct;
describe("تجميعة تبويب كل", () => {
  it("تعرض أصناف جميع الفئات في تبويب كل", () => expect(shouldShowStoreProduct(product, { title: "كل" })).toBe(true));
  it("تبقي بقية التبويبات مقيدة بالفئة المقابلة", () => { expect(shouldShowStoreProduct(product, { title: "نسائي" })).toBe(false); expect(shouldShowStoreProduct(product, { title: "أطفال" })).toBe(true); });
  it("يعرض الصنف في كل الفئات المرتبطة به", () => expect(shouldShowStoreProduct(product, { title: "بناتي" })).toBe(true));
});
