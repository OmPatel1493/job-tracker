"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import * as api from "@/lib/api";
import type { User } from "@/lib/types";

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  register: (email: string, password: string, full_name: string) => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

function setTokenCookie(token: string) {
  document.cookie = `access_token=${token}; path=/; max-age=604800`;
}

function clearTokenCookie() {
  document.cookie = "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
}

export default function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  // On mount: restore session from stored token
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setIsLoading(false);
      return;
    }
    api
      .getMe()
      .then((res) => setUser(res.data))
      .catch(() => {
        localStorage.clear();
        clearTokenCookie();
      })
      .finally(() => setIsLoading(false));
  }, []);

  async function login(email: string, password: string): Promise<void> {
    const res = await api.login(email, password);
    const token = res.data.access_token;
    localStorage.setItem("access_token", token);
    setTokenCookie(token);
    const meRes = await api.getMe();
    setUser(meRes.data);
  }

  function logout(): void {
    localStorage.clear();
    clearTokenCookie();
    setUser(null);
    router.push("/login");
  }

  async function register(
    email: string,
    password: string,
    full_name: string
  ): Promise<void> {
    await api.register(email, password, full_name);
    await login(email, password);
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: user !== null,
        login,
        logout,
        register,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
