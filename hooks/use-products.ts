import { useCallback, useEffect, useState } from "react";

import { getProducts, type StoreProduct } from "@/lib/product-api";
import { apiCall } from "@/lib/_core/api";
import { useAuth } from "@/hooks/use-auth";

export function useProducts() {
  const { user } = useAuth();
  const [products, setProducts] = useState<StoreProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const refresh = useCallback(async () => {
    try { setLoading(true); const [items, pricing] = await Promise.all([getProducts(), apiCall<{ outsideIbbMarkupPercent: number }>("/api/pricing-settings")]); const factor = user?.governorate && user.governorate !== "إب" ? 1 + pricing.outsideIbbMarkupPercent / 100 : 1; setProducts(items.map((item) => ({ ...item, price: Math.round(item.price * factor), originalPrice: Math.round(item.originalPrice * factor) }))); }
    catch { setProducts([]); }
    finally { setLoading(false); }
  }, [user?.governorate]);
  useEffect(() => { refresh(); }, [refresh]);
  return { products, loading, refresh };
}
