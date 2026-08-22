import { useCallback, useEffect, useState } from "react";

import { getCategories, type StoreCategory } from "@/lib/category-api";

export function useCategories() {
  const [categories, setCategories] = useState<StoreCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      setCategories(await getCategories());
    } catch {
      setCategories([]);
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { refresh(); }, [refresh]);
  return { categories, loading, refresh };
}
