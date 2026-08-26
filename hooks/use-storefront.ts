import { useCallback, useEffect, useState } from "react";
import { getStorefront, type StorefrontTab, type StorefrontTheme } from "@/lib/storefront-api";

export function useStorefront() {
  const [tabs, setTabs] = useState<StorefrontTab[]>([]);
  const [theme, setTheme] = useState<StorefrontTheme | null>(null);
  const [loading, setLoading] = useState(true);
  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const result = await getStorefront();
      setTabs(result.tabs);
      setTheme(result.theme);
    } catch {
      setTabs([]);
      setTheme(null);
    } finally { setLoading(false); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  return { tabs, theme, loading, refresh };
}
