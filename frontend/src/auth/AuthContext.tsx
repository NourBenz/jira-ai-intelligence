import { useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { apiRequest, clearStoredToken, getStoredToken, storeToken } from "../api/client";
import { DEMO_MODE_KEY, isDemoMode } from "../api/demo";
import type { CurrentUser, TokenResponse } from "../api/types";

interface AuthState {
  user: CurrentUser | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  enterDemo: () => void;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const demoUser: CurrentUser = { id: 0, username: "demo-viewer", role: "viewer", administered_project_keys: [] };
  const [user, setUser] = useState<CurrentUser | null>(() => isDemoMode() ? demoUser : null);
  const [loading, setLoading] = useState(Boolean(getStoredToken()) && !isDemoMode());

  useEffect(() => {
    const expire = () => {
      queryClient.clear();
      setUser(null);
    };
    window.addEventListener("jira-auth-expired", expire);
    if (getStoredToken()) {
      apiRequest<CurrentUser>("/api/auth/me")
        .then(setUser)
        .catch(() => clearStoredToken())
        .finally(() => setLoading(false));
    }
    return () => window.removeEventListener("jira-auth-expired", expire);
  }, [queryClient]);

  const value = useMemo<AuthState>(
    () => ({
      user,
      loading,
      login: async (username, password) => {
        queryClient.clear();
        localStorage.setItem(DEMO_MODE_KEY, "false");
        const token = await apiRequest<TokenResponse>("/api/auth/login", {
          method: "POST",
          body: JSON.stringify({ username, password }),
        });
        storeToken(token.access_token);
        try {
          setUser(await apiRequest<CurrentUser>("/api/auth/me"));
        } catch (error) {
          clearStoredToken();
          throw error;
        }
      },
      enterDemo: () => {
        queryClient.clear();
        clearStoredToken();
        localStorage.setItem(DEMO_MODE_KEY, "true");
        setUser(demoUser);
      },
      logout: () => {
        queryClient.clear();
        clearStoredToken();
        localStorage.setItem(DEMO_MODE_KEY, "false");
        setUser(null);
      },
    }),
    [loading, queryClient, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
