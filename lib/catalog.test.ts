import { describe, expect, it } from "vitest";

import { formatYER, products } from "./catalog";

describe("كتالوج المتجر", () => {
  it("يبدأ فارغًا حتى يضيف المدير أصنافًا", () => expect(products).toEqual([]));
  it("ينسق السعر بالريال اليمني", () => expect(formatYER(21400)).toContain("ر.ي"));
});
