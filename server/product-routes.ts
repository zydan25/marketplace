import type { Express, Request, Response } from "express";

import * as db from "./db";
import { sdk } from "./_core/sdk";
import { storagePut } from "./storage";

type UploadedImage = { dataUrl?: unknown; fileName?: unknown; sortOrder?: unknown };

export function sanitizeProductInput(body: Record<string, unknown>, images: db.ProductImageInput[]): db.ProductInput {
  const value = (key: string) => typeof body[key] === "string" ? body[key].trim() : "";
  const number = (key: string) => Number(body[key]);
  const colors = Array.isArray(body.colors) ? body.colors.map((item) => ({ name: typeof item?.name === "string" ? item.name.trim() : "", hex: typeof item?.hex === "string" ? item.hex.trim() : "" })).filter((item) => item.name && /^#[0-9a-fA-F]{6}$/.test(item.hex)) : [];
  const sizes = Array.isArray(body.sizes) ? body.sizes.map((item) => ({ label: typeof item?.label === "string" ? item.label.trim() : "", stock: Math.max(0, Number(item?.stock) || 0) })).filter((item) => item.label) : [];
  const categories = Array.isArray(body.categories) ? [...new Set(body.categories.filter((item): item is string => typeof item === "string").map((item) => item.trim()).filter(Boolean))] : [];
  const trendTags = Array.isArray(body.trendTags) ? [...new Set(body.trendTags.filter((item): item is string => typeof item === "string").map((item) => item.trim().replace(/^#/, "")).filter(Boolean))] : [];
  const category = categories[0] ?? value("category");
  const input = { productCode: value("productCode").toUpperCase(), name: value("name"), category, categories: categories.length ? categories : category ? [category] : [], description: value("description"), details: value("details"), material: value("material"), price: number("price"), discountPercent: number("discountPercent"), shippingNote: value("shippingNote"), isTrending: body.isTrending === true, trendTags, isPublished: body.isPublished !== false, colors, sizes, images };
  if (!input.name || !input.category || !input.description) throw new Error("الاسم والفئة والوصف مطلوبة.");
  if (input.productCode && !/^[A-Z0-9-]{3,80}$/.test(input.productCode)) throw new Error("رقم الصنف يجب أن يحتوي أحرفًا أو أرقامًا أو شرطات فقط.");
  if (!Number.isInteger(input.price) || input.price <= 0) throw new Error("أدخلي سعرًا صحيحًا أكبر من صفر.");
  if (!Number.isInteger(input.discountPercent) || input.discountPercent < 0 || input.discountPercent > 90) throw new Error("نسبة الخصم يجب أن تكون بين 0 و90.");
  if (input.isTrending && !input.trendTags.length) throw new Error("أضيفي هاشتاج ترند واحدًا على الأقل للصنف المفعّل في الترندات.");
  return input;
}

async function requireAdmin(req: Request, res: Response) {
  try { const user = await sdk.authenticateRequest(req); if (user.role !== "admin") { res.status(403).json({ error: "هذه العملية مخصصة للمدير." }); return undefined; } return user; }
  catch { res.status(401).json({ error: "سجّلي الدخول بحساب المدير أولًا." }); return undefined; }
}

async function uploadImages(images: UploadedImage[]) {
  if (images.length > 10) throw new Error("يمكن إضافة 10 صور كحد أقصى للصنف الواحد.");
  return Promise.all(images.map(async (image, index) => {
    if (typeof image.dataUrl !== "string") throw new Error("تعذر قراءة إحدى الصور المختارة.");
    const match = image.dataUrl.match(/^data:(image\/(?:jpeg|jpg|png|webp));base64,([A-Za-z0-9+/=]+)$/);
    if (!match) throw new Error("صيغة صورة غير مدعومة.");
    const extension = match[1] === "image/png" ? "png" : match[1] === "image/webp" ? "webp" : "jpg";
    const uploaded = await storagePut(`products/${Date.now()}-${index}.${extension}`, Buffer.from(match[2], "base64"), match[1]);
    return { storageKey: uploaded.key, url: uploaded.url, sortOrder: Number(image.sortOrder) || index };
  }));
}

export function registerProductRoutes(app: Express) {
  app.get("/api/products", async (req, res) => res.json({ products: await db.searchProducts(typeof req.query.q === "string" ? req.query.q : "") }));
  app.get("/api/products/:id", async (req, res) => { const product = await db.getProduct(Number(req.params.id)); if (!product) { res.status(404).json({ error: "الصنف غير موجود." }); return; } res.json({ product, similar: await db.findSimilarProducts(Number(req.params.id), product.category) }); });
  app.get("/api/admin/products", async (req, res) => { if (!await requireAdmin(req, res)) return; res.json({ products: await db.listProducts(true) }); });
  app.post("/api/admin/products", async (req, res) => { const user = await requireAdmin(req, res); if (!user) return; try { const uploaded = await uploadImages(Array.isArray(req.body?.images) ? req.body.images : []); const product = await db.createProduct(sanitizeProductInput(req.body ?? {}, uploaded), user.id); res.status(201).json({ product }); } catch (error) { res.status(400).json({ error: error instanceof Error ? error.message : "تعذر حفظ الصنف." }); } });
  app.patch("/api/admin/products/:id", async (req, res) => { if (!await requireAdmin(req, res)) return; try { const uploaded = await uploadImages(Array.isArray(req.body?.newImages) ? req.body.newImages : []); const retained = Array.isArray(req.body?.existingImages) ? req.body.existingImages.filter((item: unknown): item is db.ProductImageInput => Boolean(item && typeof (item as db.ProductImageInput).storageKey === "string" && typeof (item as db.ProductImageInput).url === "string")).map((item: db.ProductImageInput, index: number) => ({ ...item, sortOrder: index })) : []; const product = await db.updateProduct(Number(req.params.id), sanitizeProductInput(req.body ?? {}, [...retained, ...uploaded.map((item, index) => ({ ...item, sortOrder: retained.length + index }))])); res.json({ product }); } catch (error) { res.status(400).json({ error: error instanceof Error ? error.message : "تعذر تعديل الصنف." }); } });
}
