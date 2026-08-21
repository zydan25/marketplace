import type { Express } from "express";
import { invokeLLM } from "./_core/llm";
import * as db from "./db";

export function registerVisualSearchRoutes(app: Express) {
  app.post("/api/products/visual-search", async (req, res) => {
    try {
      const imageUrl = typeof req.body?.imageDataUrl === "string" ? req.body.imageDataUrl : "";
      if (!/^data:image\/(jpeg|jpg|png|webp);base64,/.test(imageUrl)) throw new Error("اختاري صورة صالحة من المعرض.");
      if (imageUrl.length > 6_000_000) throw new Error("الصورة كبيرة جدًا للبحث؛ اختاري نسخة أصغر.");
      const catalog = await db.listProducts(false);
      if (!catalog.length) return res.json({ products: [], query: "" });
      const response = await invokeLLM({ model: "gemini-3-flash-preview", messages: [{ role: "system", content: "استخرج كلمات بحث عربية دقيقة تصف قطعة الأزياء في الصورة، مثل النوع واللون والخامة والنقشة. أعد JSON فقط بالشكل {\"query\":\"...\"}." }, { role: "user", content: [{ type: "text", text: "حلل هذه الصورة للبحث في كتالوج أزياء." }, { type: "image_url", image_url: { url: imageUrl, detail: "low" } }] }], response_format: { type: "json_object" } });
      const raw = response.choices[0]?.message.content; const parsed = typeof raw === "string" ? JSON.parse(raw) as { query?: string } : {}; const query = typeof parsed.query === "string" ? parsed.query.slice(0, 160) : "";
      const keywords = query.split(/\s+/).filter((term) => term.length > 2); const matches = catalog.map((product) => ({ product, score: keywords.filter((term) => [product.name, product.description, product.category, ...product.trendTags].join(" ").includes(term)).length })).filter((entry) => entry.score > 0).sort((a, b) => b.score - a.score).map((entry) => entry.product);
      res.json({ products: matches.length ? matches : catalog.slice(0, 12), query });
    } catch (error) { res.status(400).json({ error: error instanceof Error ? error.message : "تعذر إتمام البحث بالصورة." }); }
  });
}
