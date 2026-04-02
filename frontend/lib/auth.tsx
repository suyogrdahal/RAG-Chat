"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  useEffect,
  type ReactNode
} from "react";
import { useRouter } from "next/navigation";
import { api, setAuthToken, setAuthTokens, clearAuthTokens } from "./api";

type AuthContextValue = {
  token: string | null;
  isAuthenticated: boolean;
  isReady: boolean;
  login: (email: string, password: string) => Promise<void>;
  setSession: (token: string) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [isReady, setIsReady] = useState(false);

  const setSession = useCallback((accessToken: string) => {
    setToken(accessToken);
    setAuthTokens(accessToken);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const { data } = await api.post<{ access_token: string; refresh_token: string }>(
        "/auth/login",
        {
          email,
          password
        }
      );
      const accessToken = data.access_token;
      const refreshToken = data.refresh_token;
      setToken(accessToken);
      setAuthTokens(accessToken, refreshToken);
      router.push("/dashboard");
    },
    [router]
  );

  const logout = useCallback(() => {
    setToken(null);
    clearAuthTokens();
    router.push("/login");
  }, [router]);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      isAuthenticated: Boolean(token),
      isReady,
      login,
      setSession,
      logout
    }),
    [token, isReady, login, setSession, logout]
  );

  useEffect(() => {
    if (typeof window === "undefined") return;
    const saved = sessionStorage.getItem("access_token");
    if (saved) {
      setAuthToken(saved);
      setToken(saved);
    }
    setIsReady(true);
  }, []);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
