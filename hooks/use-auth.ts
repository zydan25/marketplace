import * as Api from "@/lib/_core/api";
import * as Auth from "@/lib/_core/auth";
import { useCallback, useEffect, useMemo, useState } from "react";

type UseAuthOptions = {
  autoFetch?: boolean;
};

export function useAuth(options?: UseAuthOptions) {
  const { autoFetch = true } = options ?? {};
  const [user, setUser] = useState<Auth.User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchUser = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const token = await Auth.getSessionToken();
      if (!token) {
        setUser(null);
        return;
      }

      // Use cached identity immediately so navigation survives refreshes on Web
      // and native, then validate/refresh it against Django using the token.
      const cachedUser = await Auth.getUserInfo();
      if (cachedUser) setUser(cachedUser);

      const apiUser = await Api.getMe();
      if (apiUser) {
        const userInfo: Auth.User = {
          id: apiUser.id,
          openId: apiUser.openId,
          name: apiUser.name,
          email: apiUser.email,
          phone: apiUser.phone,
          governorate: apiUser.governorate,
          loginMethod: apiUser.loginMethod,
          role: apiUser.role,
          lastSignedIn: cachedUser?.lastSignedIn ?? new Date(apiUser.lastSignedIn),
        };
        setUser(userInfo);
        await Auth.setUserInfo(userInfo);
      } else if (!cachedUser) {
        await Auth.removeSessionToken();
        setUser(null);
      }
    } catch (err) {
      const authError = err instanceof Error ? err : new Error("تعذر التحقق من جلسة الدخول.");
      setError(authError);
      // Keep a valid cached identity during transient network failures.
      const cachedUser = await Auth.getUserInfo();
      setUser(cachedUser);
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await Api.logout();
    } catch (err) {
      console.error("[Auth] Logout API call failed:", err);
    } finally {
      await Auth.removeSessionToken();
      await Auth.clearUserInfo();
      setUser(null);
      setError(null);
    }
  }, []);

  const isAuthenticated = useMemo(() => Boolean(user), [user]);

  useEffect(() => {
    if (autoFetch) {
      void fetchUser();
    } else {
      setLoading(false);
    }
  }, [autoFetch, fetchUser]);

  return {
    user,
    loading,
    error,
    isAuthenticated,
    refresh: fetchUser,
    logout,
  };
}
