import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { getAuthToken, removeAuthToken, setAuthToken } from "./theme";

const AUTH_USER_KEY = "meeting_organizer_user";

export interface User {
  id: number;
  name: string;
  email: string;
  role: "chairman" | "principal" | "hod" | "teacher" | "student";
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (token: string, user: User) => void;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function readCachedUser(): User | null {
  if (!getAuthToken()) return null;
  try {
    const value: unknown = JSON.parse(localStorage.getItem(AUTH_USER_KEY) || "null");
    if (
      typeof value === "object" &&
      value !== null &&
      "id" in value &&
      typeof value.id === "number" &&
      "name" in value &&
      typeof value.name === "string" &&
      "email" in value &&
      typeof value.email === "string" &&
      "role" in value &&
      ["chairman", "principal", "hod", "teacher", "student"].includes(String(value.role))
    ) {
      return value as User;
    }
  } catch {
    localStorage.removeItem(AUTH_USER_KEY);
  }
  return null;
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setTokenState] = useState<string | null>(getAuthToken());
  const [user, setUser] = useState<User | null>(readCachedUser);
  const [loading, setLoading] = useState<boolean>(
    () => Boolean(getAuthToken()) && !readCachedUser(),
  );

  useEffect(() => {
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }

    api.get<User>("/auth/me")
      .then((userData) => {
        setUser(userData);
        localStorage.setItem(AUTH_USER_KEY, JSON.stringify(userData));
      })
      .catch((error: unknown) => {
        console.error("Session validation failed:", error);
        const message = error instanceof Error ? error.message : "";
        if (/Could not validate credentials|Not authenticated/i.test(message)) {
          removeAuthToken();
          localStorage.removeItem(AUTH_USER_KEY);
          setTokenState(null);
          setUser(null);
        }
      })
      .finally(() => setLoading(false));
  }, [token]);

  const login = (newToken: string, userData: User) => {
    setAuthToken(newToken);
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(userData));
    setTokenState(newToken);
    setUser(userData);
  };

  const logout = () => {
    removeAuthToken();
    localStorage.removeItem(AUTH_USER_KEY);
    setTokenState(null);
    setUser(null);
  };

  const value = useMemo(
    () => ({ user, token, login, logout, loading }),
    [user, token, loading],
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
