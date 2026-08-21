import { useCallback, useEffect, useState } from "react";

import { getProducts, type StoreProduct } from "@/lib/product-api";

export function useProducts() {
  const [products, setProducts] = useState<StoreProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const refresh = useCallback(async () => {
    try { setLoading(true); const items = await getProducts(); setProducts(items); }
    catch { setProducts([]); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { refresh(); }, [refresh]);
  return { products, loading, refresh };
}
