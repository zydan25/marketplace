import { asc, eq } from "drizzle-orm";
import type { Express, Request, Response } from "express";

import { storefrontCircleSections, storefrontSlides, storefrontTabs } from "../drizzle/schema";
import { getDb } from "./db";
import { sdk } from "./_core/sdk";
import { storagePut } from "./storage";

type TabPayload = { title?: unknown; searchPlaceholder?: unknown; isActive?: unknown; sortOrder?: unknown };
type VisualPayload = { title?: unknown; subtitle?: unknown; ctaLabel?: unknown; targetCategory?: unknown; isActive?: unknown; sortOrder?: unknown; image?: unknown };
type ImageInput = { dataUrl?: unknown; fileName?: unknown };

const clean = (value: unknown) => typeof value === "string" ? value.trim() : "";
const positiveInt = (value: unknown, fallback = 0) => Math.max(0, Number.isInteger(Number(value)) ? Number(value) : fallback);

async function requireAdmin(req: Request, res: Response) {
  try { const user = await sdk.authenticateRequest(req); if (user.role !== "admin") { res.status(403).json({ error: "هذه العملية مخصصة للمدير." }); return undefined; } return user; }
  catch { res.status(401).json({ error: "سجّلي الدخول بحساب المدير أولًا." }); return undefined; }
}

async function uploadImage(input: unknown, scope: string, required: boolean) {
  const image = input as ImageInput | undefined;
  if (!image?.dataUrl) { if (required) throw new Error("اختاري صورة أولًا."); return undefined; }
  if (typeof image.dataUrl !== "string") throw new Error("تعذر قراءة الصورة.");
  const match = image.dataUrl.match(/^data:(image\/(?:jpeg|jpg|png|webp));base64,([A-Za-z0-9+/=]+)$/);
  if (!match) throw new Error("صيغة الصورة غير مدعومة.");
  const extension = match[1] === "image/png" ? "png" : match[1] === "image/webp" ? "webp" : "jpg";
  return storagePut(`storefront/${scope}-${Date.now()}.${extension}`, Buffer.from(match[2], "base64"), match[1]);
}

async function storefrontData(includeInactive = false) {
  const db = await getDb(); if (!db) throw new Error("Database not available");
  const tabs = (await db.select().from(storefrontTabs).orderBy(asc(storefrontTabs.sortOrder))).filter((tab) => includeInactive || tab.isActive);
  return Promise.all(tabs.map(async (tab) => {
    const slides = (await db.select().from(storefrontSlides).where(eq(storefrontSlides.tabId, tab.id)).orderBy(asc(storefrontSlides.sortOrder))).filter((slide) => includeInactive || slide.isActive);
    const circles = (await db.select().from(storefrontCircleSections).where(eq(storefrontCircleSections.tabId, tab.id)).orderBy(asc(storefrontCircleSections.sortOrder))).filter((circle) => includeInactive || circle.isActive);
    return { id: String(tab.id), title: tab.title, searchPlaceholder: tab.searchPlaceholder ?? "ابحثي عن صنف أو ستايل", isActive: tab.isActive, sortOrder: tab.sortOrder, slides: slides.map((slide) => ({ id: String(slide.id), title: slide.title ?? "", subtitle: slide.subtitle ?? "", ctaLabel: slide.ctaLabel ?? "تسوّقي الآن", imageUrl: slide.imageUrl, storageKey: slide.storageKey, isActive: slide.isActive, sortOrder: slide.sortOrder })), circles: circles.map((circle) => ({ id: String(circle.id), title: circle.title, targetCategory: circle.targetCategory ?? "", imageUrl: circle.imageUrl ?? "", storageKey: circle.storageKey ?? "", isActive: circle.isActive, sortOrder: circle.sortOrder })) };
  }));
}

async function nextOrder(table: typeof storefrontTabs | typeof storefrontSlides | typeof storefrontCircleSections, column?: number) {
  const db = await getDb(); if (!db) throw new Error("Database not available");
  const rows = table === storefrontTabs ? await db.select().from(storefrontTabs) : table === storefrontSlides ? await db.select().from(storefrontSlides).where(eq(storefrontSlides.tabId, column ?? 0)) : await db.select().from(storefrontCircleSections).where(eq(storefrontCircleSections.tabId, column ?? 0));
  return rows.length ? Math.max(...rows.map((row) => row.sortOrder)) + 1 : 0;
}

export function registerStorefrontRoutes(app: Express) {
  app.get("/api/storefront", async (_req, res) => { try { res.json({ tabs: await storefrontData(false) }); } catch { res.status(500).json({ error: "تعذر تحميل واجهة المتجر." }); } });
  app.get("/api/admin/storefront", async (req, res) => { if (!await requireAdmin(req, res)) return; res.json({ tabs: await storefrontData(true) }); });
  app.post("/api/admin/storefront/tabs", async (req, res) => { const user = await requireAdmin(req, res); if (!user) return; const body = req.body as TabPayload; const title = clean(body.title); if (!title) { res.status(400).json({ error: "اسم التبويب مطلوب." }); return; } const db = await getDb(); if (!db) { res.status(503).json({ error: "قاعدة البيانات غير متاحة." }); return; } await db.insert(storefrontTabs).values({ title, searchPlaceholder: clean(body.searchPlaceholder) || null, isActive: body.isActive !== false, sortOrder: await nextOrder(storefrontTabs), createdByUserId: user.id }); res.status(201).json({ tabs: await storefrontData(true) }); });
  app.patch("/api/admin/storefront/tabs/:id", async (req, res) => { if (!await requireAdmin(req, res)) return; const body = req.body as TabPayload; const title = clean(body.title); const db = await getDb(); if (!db) { res.status(503).json({ error: "قاعدة البيانات غير متاحة." }); return; } await db.update(storefrontTabs).set({ ...(title ? { title } : {}), ...(body.searchPlaceholder !== undefined ? { searchPlaceholder: clean(body.searchPlaceholder) || null } : {}), ...(body.isActive !== undefined ? { isActive: body.isActive === true } : {}), ...(body.sortOrder !== undefined ? { sortOrder: positiveInt(body.sortOrder) } : {}) }).where(eq(storefrontTabs.id, Number(req.params.id))); res.json({ tabs: await storefrontData(true) }); });
  app.delete("/api/admin/storefront/tabs/:id", async (req, res) => { if (!await requireAdmin(req, res)) return; const id = Number(req.params.id); const db = await getDb(); if (!db) { res.status(503).json({ error: "قاعدة البيانات غير متاحة." }); return; } await db.delete(storefrontSlides).where(eq(storefrontSlides.tabId, id)); await db.delete(storefrontCircleSections).where(eq(storefrontCircleSections.tabId, id)); await db.delete(storefrontTabs).where(eq(storefrontTabs.id, id)); res.json({ tabs: await storefrontData(true) }); });
  app.post("/api/admin/storefront/tabs/:id/slides", async (req, res) => { if (!await requireAdmin(req, res)) return; try { const body = req.body as VisualPayload; const image = await uploadImage(body.image, `slide-${req.params.id}`, true); const db = await getDb(); if (!db || !image) throw new Error("تعذر رفع الصورة."); await db.insert(storefrontSlides).values({ tabId: Number(req.params.id), title: clean(body.title) || null, subtitle: clean(body.subtitle) || null, ctaLabel: clean(body.ctaLabel) || null, storageKey: image.key, imageUrl: image.url, sortOrder: await nextOrder(storefrontSlides, Number(req.params.id)), isActive: body.isActive !== false }); res.status(201).json({ tabs: await storefrontData(true) }); } catch (error) { res.status(400).json({ error: error instanceof Error ? error.message : "تعذر إضافة العرض." }); } });
  app.delete("/api/admin/storefront/slides/:id", async (req, res) => { if (!await requireAdmin(req, res)) return; const db = await getDb(); if (!db) { res.status(503).json({ error: "قاعدة البيانات غير متاحة." }); return; } await db.delete(storefrontSlides).where(eq(storefrontSlides.id, Number(req.params.id))); res.json({ tabs: await storefrontData(true) }); });
  app.patch("/api/admin/storefront/slides/:id", async (req, res) => { if (!await requireAdmin(req, res)) return; const body = req.body as VisualPayload; const db = await getDb(); if (!db) { res.status(503).json({ error: "قاعدة البيانات غير متاحة." }); return; } await db.update(storefrontSlides).set({ ...(body.isActive !== undefined ? { isActive: body.isActive === true } : {}), ...(body.sortOrder !== undefined ? { sortOrder: positiveInt(body.sortOrder) } : {}) }).where(eq(storefrontSlides.id, Number(req.params.id))); res.json({ tabs: await storefrontData(true) }); });
  app.post("/api/admin/storefront/tabs/:id/circles", async (req, res) => { if (!await requireAdmin(req, res)) return; try { const body = req.body as VisualPayload; const title = clean(body.title); if (!title) throw new Error("اسم القسم الدائري مطلوب."); const image = await uploadImage(body.image, `circle-${req.params.id}`, false); const db = await getDb(); if (!db) throw new Error("قاعدة البيانات غير متاحة."); await db.insert(storefrontCircleSections).values({ tabId: Number(req.params.id), title, targetCategory: clean(body.targetCategory) || null, storageKey: image?.key ?? null, imageUrl: image?.url ?? null, sortOrder: await nextOrder(storefrontCircleSections, Number(req.params.id)), isActive: body.isActive !== false }); res.status(201).json({ tabs: await storefrontData(true) }); } catch (error) { res.status(400).json({ error: error instanceof Error ? error.message : "تعذر إضافة القسم." }); } });
  app.delete("/api/admin/storefront/circles/:id", async (req, res) => { if (!await requireAdmin(req, res)) return; const db = await getDb(); if (!db) { res.status(503).json({ error: "قاعدة البيانات غير متاحة." }); return; } await db.delete(storefrontCircleSections).where(eq(storefrontCircleSections.id, Number(req.params.id))); res.json({ tabs: await storefrontData(true) }); });
  app.patch("/api/admin/storefront/circles/:id", async (req, res) => { if (!await requireAdmin(req, res)) return; const body = req.body as VisualPayload; const db = await getDb(); if (!db) { res.status(503).json({ error: "قاعدة البيانات غير متاحة." }); return; } await db.update(storefrontCircleSections).set({ ...(body.isActive !== undefined ? { isActive: body.isActive === true } : {}), ...(body.sortOrder !== undefined ? { sortOrder: positiveInt(body.sortOrder) } : {}) }).where(eq(storefrontCircleSections.id, Number(req.params.id))); res.json({ tabs: await storefrontData(true) }); });
}
