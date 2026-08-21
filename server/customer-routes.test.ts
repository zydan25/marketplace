import { describe, expect, it } from "vitest";

import { sanitizeReward } from "./customer-routes";

describe("حوافز العملاء", () => {
  it("يتحقق من بيانات كوبون العميل ويحول رمزه إلى أحرف كبيرة", () => {
    const reward = sanitizeReward({ rewardType: "coupon", title: "خصم خاص", couponCode: " bashir20 ", discountType: "fixed", discountValue: 2000, minimumOrderAmount: 10000 });
    expect(reward.couponCode).toBe("BASHIR20");
    expect(reward.minimumOrderAmount).toBe(10000);
  });
  it("يرفض الكوبون بلا رمز والخصم الذي يتجاوز الحد", () => {
    expect(() => sanitizeReward({ rewardType: "coupon", title: "خصم", discountType: "fixed", discountValue: 1000 })).toThrow("رمز الكوبون");
    expect(() => sanitizeReward({ rewardType: "order_threshold", title: "خصم", discountType: "percent", discountValue: 91 })).toThrow("90%");
  });
});
