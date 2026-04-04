/* eslint-disable react-refresh/only-export-components */

import {
  createContext,
  useContext,
  useMemo,
  useState,
} from "react";
import type { PropsWithChildren } from "react";

import type { AuthSession, BackendAuthSession } from "./types";

const STORAGE_KEY = "splitmint.auth";

function loadSession(): AuthSession | null {
  const rawValue = window.localStorage.getItem(STORAGE_KEY);
  if (!rawValue) return null;

  try {
    return JSON.parse(rawValue) as AuthSession;
  } catch {
    window.localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

function saveSession(session: AuthSession | null) {
  if (!session) {
    window.localStorage.removeItem(STORAGE_KEY);
    return;
  }

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export function normalizeAuthSession(payload: BackendAuthSession): AuthSession {
  return {
    user: payload.user,
    accessToken: payload.tokens.access_token,
    refreshToken: payload.tokens.refresh_token,
    tokenType: payload.tokens.token_type,
    expiresInSeconds: payload.tokens.expires_in_seconds,
  };
}

type AuthContextValue = {
  session: AuthSession | null;
  setSession: (session: AuthSession | null) => void;
  clearSession: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [session, setSessionState] = useState<AuthSession | null>(() => loadSession());

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      setSession(nextSession) {
        saveSession(nextSession);
        setSessionState(nextSession);
      },
      clearSession() {
        saveSession(null);
        setSessionState(null);
      },
    }),
    [session],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }

  return context;
}
