import { describe, expect, it } from "vitest";

import { hashAdminPassword, verifyAdminPassword } from "./admin-password";

describe("حماية كلمة مرور الإدارة", () => {
  it("يُخزّن كلمة المرور بتجزئة مملحة قابلة للتحقق", () => {
    const hash = hashAdminPassword("admin-secret", Buffer.alloc(16, 7));
    expect(hash).not.toContain("admin-secret");
    expect(verifyAdminPassword("admin-secret", hash)).toBe(true);
    expect(verifyAdminPassword("wrong-secret", hash)).toBe(false);
  });
});
