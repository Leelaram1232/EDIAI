"use client";
import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { User, TokenResponse } from "@/types/api";
import api from "@/lib/api";

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, name: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check for stored auth
    const stored = localStorage.getItem("auth_user");
    const token = localStorage.getItem("auth_token");
    if (stored && token) {
      try {
        setUser(JSON.parse(stored));
      } catch {
        localStorage.removeItem("auth_user");
        localStorage.removeItem("auth_token");
      }
    } else {
      // Mock user for easy dashboard testing without login
      const mockUser: User = {
        id: "mock-test-id",
        email: "test@ediai.com",
        name: "Test User",
        role: "admin",
        is_active: true,
        created_at: new Date().toISOString()
      };
      setUser(mockUser);
      localStorage.setItem("auth_token", "mock-token-for-test");
      localStorage.setItem("auth_user", JSON.stringify(mockUser));
    }
    setIsLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    const res = await api.post<TokenResponse>("/auth/login", { email, password });
    localStorage.setItem("auth_token", res.access_token);
    localStorage.setItem("auth_user", JSON.stringify(res.user));
    setUser(res.user);
  };

  const signup = async (email: string, name: string, password: string) => {
    await api.post("/auth/signup", { email, name, password });
  };

  const logout = () => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
    setUser(null);
    window.location.href = "/login";
  };

  return (
    <AuthContext.Provider
      value={{ user, isLoading, isAuthenticated: !!user, login, signup, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
