import { describe, expect, it } from "vitest";

import { normalizePhone, validateRegistration } from "./phone-auth";

describe("مصادقة الهاتف", () => {
  it("ينظف رقم الهاتف من المسافات والرموز", () => {
    expect(normalizePhone("771 053 370")).toBe("771053370");
  });

  it("يقبل بيانات التسجيل الصحيحة في محافظة يمنية", () => {
    const result = validateRegistration({ firstName: "بشير", secondName: "محمد", thirdName: "أحمد", familyName: "النعماني", phone: "771053370", password: "valid-password", governorate: "إب" });
    expect(result.valid).toBe(true);
  });

  it("يرفض المحافظة غير الموجودة في قائمة اليمن", () => {
    const result = validateRegistration({ firstName: "بشير", secondName: "محمد", thirdName: "أحمد", familyName: "النعماني", phone: "771053370", password: "valid-password", governorate: "محافظة غير صالحة" });
    expect(result.valid).toBe(false);
  });
});
