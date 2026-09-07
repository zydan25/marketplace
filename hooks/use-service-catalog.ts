import { useCallback, useEffect, useState } from "react";
import { getServiceCatalog, type ServiceCatalogResponse } from "@/lib/service-catalog";

export function useServiceCatalog() {
  const [catalog, setCatalog] = useState<ServiceCatalogResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const refresh = useCallback(async () => {
    try { setLoading(true); setError(""); setCatalog(await getServiceCatalog()); }
    catch (reason) { setCatalog(null); setError(reason instanceof Error ? reason.message : "تعذر تحميل خدمات الاتصالات والألعاب والبطائق."); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { refresh(); }, [refresh]);
  return { catalog, loading, error, refresh };
}
