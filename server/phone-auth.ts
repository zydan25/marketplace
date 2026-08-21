import type { Express, Request, Response } from "express";

import { createPhoneUser, getUserByPhone, recordReferral } from "./db";
import { hashAdminPassword, verifyAdminPassword } from "./admin-password";
import { getSessionCookieOptions } from "./_core/cookies";
import { sdk } from "./_core/sdk";
import { COOKIE_NAME, ONE_YEAR_MS } from "../shared/const";

export const YEMEN_GOVERNORATES = [
  "أمانة العاصمة", "عدن", "أبين", "البيضاء", "الضالع", "الحديدة", "الجوف", "المهرة", "المحويت", "عمران", "ذمار", "حضرموت", "حجة", "إب", "لحج", "مأرب", "ريمة", "صعدة", "صنعاء", "شبوة", "سقطرى", "تعز",
] as const;

type RegistrationInput = {
  firstName?: unknown;
  secondName?: unknown;
  thirdName?: unknown;
  familyName?: unknown;
  phone?: unknown;
  password?: unknown;
  governorate?: unknown;
};

type RegistrationData = {
  firstName: string;
  secondName: string;
  thirdName: string;
  familyName: string;
  phone: string;
  password: string;
  governorate: string;
};

export function normalizePhone(value: unknown): string {
  return typeof value === "string" ? value.replace(/[^0-9]/g, "") : "";
}

export function validateRegistration(input: RegistrationInput): { valid: true; data: RegistrationData } | { valid: false; error: string } {
  const firstName = typeof input.firstName === "string" ? input.firstName.trim() : "";
  const secondName = typeof input.secondName === "string" ? input.secondName.trim() : "";
  const thirdName = typeof input.thirdName === "string" ? input.thirdName.trim() : "";
  const familyName = typeof input.familyName === "string" ? input.familyName.trim() : "";
  const password = typeof input.password === "string" ? input.password : "";
  const governorate = typeof input.governorate === "string" ? input.governorate.trim() : "";
  const phone = normalizePhone(input.phone);
  if (![firstName, secondName, thirdName, familyName].every((part) => part.length >= 2)) return { valid: false, error: "أدخلي الاسم الأول والثاني والثالث واللقب بصورة صحيحة." };
  if (!/^\d{9,12}$/.test(phone)) return { valid: false, error: "أدخلي رقم جوال صحيحًا." };
  if (password.length < 8) return { valid: false, error: "كلمة المرور يجب أن تتكون من 8 أحرف أو أرقام على الأقل." };
  if (!YEMEN_GOVERNORATES.includes(governorate as typeof YEMEN_GOVERNORATES[number])) return { valid: false, error: "اختاري محافظة من القائمة." };
  return { valid: true, data: { firstName, secondName, thirdName, familyName, phone, password, governorate } };
}

function userResponse(user: NonNullable<Awaited<ReturnType<typeof getUserByPhone>>>) {
  return { id: user.id, openId: user.openId, name: user.name, email: user.email, phone: user.phone, governorate: user.governorate, loginMethod: user.loginMethod, role: user.role, lastSignedIn: user.lastSignedIn.toISOString() };
}

async function issueSession(req: Request, res: Response, user: NonNullable<Awaited<ReturnType<typeof getUserByPhone>>>) {
  const sessionToken = await sdk.createSessionToken(user.openId, { name: user.name ?? "عميل", expiresInMs: ONE_YEAR_MS });
  res.cookie(COOKIE_NAME, sessionToken, { ...getSessionCookieOptions(req), maxAge: ONE_YEAR_MS });
  res.json({ sessionToken, user: userResponse(user) });
}

export function registerPhoneAuthRoutes(app: Express) {
  app.post("/api/phone-auth/login", async (req: Request, res: Response) => {
    const phone = normalizePhone(req.body?.phone);
    const password = typeof req.body?.password === "string" ? req.body.password : "";
    if (!phone || !password) { res.status(400).json({ error: "رقم الجوال وكلمة المرور مطلوبان." }); return; }
    const user = await getUserByPhone(phone);
    if (!user?.passwordHash || !verifyAdminPassword(password, user.passwordHash)) { res.status(401).json({ error: "رقم الجوال أو كلمة المرور غير صحيحة." }); return; }
    await issueSession(req, res, user);
  });

  app.post("/api/phone-auth/register", async (req: Request, res: Response) => {
    const check = validateRegistration(req.body ?? {});
    if (!check.valid) { res.status(400).json({ error: check.error }); return; }
    if (await getUserByPhone(check.data.phone)) { res.status(409).json({ error: "رقم الجوال مسجل بالفعل. سجّلي الدخول بدلًا من ذلك." }); return; }
    const { firstName, secondName, thirdName, familyName, phone, password, governorate } = check.data;
    const name = [firstName, secondName, thirdName, familyName].join(" ");
    const user = await createPhoneUser({ openId: `phone-user-${phone}`, name, firstName, secondName, thirdName, familyName, governorate, phone, passwordHash: hashAdminPassword(password) });
    if (!user) { res.status(500).json({ error: "تعذر إنشاء الحساب. حاولي مجددًا." }); return; }
    await recordReferral(user.id, typeof req.body?.referralCode === "string" ? req.body.referralCode.trim().toUpperCase() : undefined);
    await issueSession(req, res, user);
  });
}
