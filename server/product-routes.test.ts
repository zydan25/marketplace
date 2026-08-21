import { describe, expect, it } from "vitest";

import { sanitizeProductInput } from "./product-routes";

describe("بيانات الصنف", () => {
  const base = { name: "فستان أطفال", category: "أطفال", description: "فستان مناسب للمناسبات", details: "تطريز ناعم", material: "قطن", price: 15000, discountPercent: 20, shippingNote: "شحن مجاني", colors: [{ name: "أزرق", hex: "#3F6F97" }], sizes: [{ label: "4Y", stock: 6 }], isPublished: true };
  it("يحوّل بيانات الصنف الصحيحة إلى عقد تخزين آمن", () => {
    const product = sanitizeProductInput(base, []);
    expect(product.price).toBe(15000);
    expect(product.discountPercent).toBe(20);
    expect(product.colors[0].hex).toBe("#3F6F97");
  });
  it("يقبل ربط الصنف بفئات متعددة دون تكرار", () => {
    const product = sanitizeProductInput({ ...base, categories: ["أطفال", "بناتي", "أطفال"] }, []);
    expect(product.categories).toEqual(["أطفال", "بناتي"]);
    expect(product.category).toBe("أطفال");
  });
  it("يرفض السعر غير الصحيح أو خصمًا خارج الحد المسموح", () => {
    expect(() => sanitizeProductInput({ ...base, price: 0 }, [])).toThrow("سعرًا صحيحًا");
    expect(() => sanitizeProductInput({ ...base, discountPercent: 91 }, [])).toThrow("نسبة الخصم");
  });
  it("يتطلب هاشتاجًا عند تفعيل الترندات ويطبع علامة الهاشتاج", () => {
    expect(() => sanitizeProductInput({ ...base, isTrending: true }, [])).toThrow("هاشتاج ترند");
    expect(sanitizeProductInput({ ...base, isTrending: true, trendTags: ["#إطلالة_العيد", "إطلالة_العيد"] }, []).trendTags).toEqual(["إطلالة_العيد"]);
  });
});
