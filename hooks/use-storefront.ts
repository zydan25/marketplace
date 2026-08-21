import { useCallback, useEffect, useState } from "react";

import { getStorefront, type StorefrontTab } from "@/lib/storefront-api";

export function useStorefront() {
  const [tabs, setTabs] = useState<StorefrontTab[]>([]);
  const [loading, setLoading] = useState(true);
  const refresh = useCallback(async () => { try { setLoading(true); setTabs(await getStorefront()); } catch { setTabs([]); } finally { setLoading(false); } }, []);
  useEffect(() => { refresh(); }, [refresh]);
  return { tabs, loading, refresh };
}
