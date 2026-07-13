import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

export interface User {
  id: number;
  username: string;
  role: string;
  status: string;
}

interface AuthContextType {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isStaff: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  apiUrl: string;
  setApiUrl: (url: string) => void;
  apiFetch: (path: string, options?: RequestInit) => Promise<Response>;
}

const AuthContext = createContext<AuthContextType | null>(null);

const TOKEN_KEY = 'lca_token';
const USER_KEY = 'lca_user';
const API_URL_KEY = 'lca_api_url';
const DEFAULT_API_URL = 'http://localhost:8000';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [apiUrl, setApiUrlState] = useState(() => localStorage.getItem(API_URL_KEY) || DEFAULT_API_URL);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<User | null>(() => {
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) return null;
    try { return JSON.parse(raw); } catch { return null; }
  });

  const isAuthenticated = !!token && !!user;
  const isAdmin = user?.role === 'ADMIN';
  const isStaff = user?.role === 'ADMIN' || user?.role === 'LIBRARIAN';

  const setApiUrl = useCallback((url: string) => {
    setApiUrlState(url);
    localStorage.setItem(API_URL_KEY, url);
  }, []);

  const apiFetch = useCallback(
    async (path: string, options?: RequestInit): Promise<Response> => {
      const base = apiUrl.trim().replace(/\/$/, '');
      const suffix = path.startsWith('/') ? path : `/${path}`;
      const headers: Record<string, string> = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const opts: RequestInit = { ...options };
      if (opts.body instanceof FormData) {
        opts.headers = headers as HeadersInit;
      } else {
        headers['Content-Type'] = 'application/json';
        opts.headers = headers as HeadersInit;
      }
      return fetch(`${base}${suffix}`, opts).then((res) => {
        if (res.status === 401) {
          logout();
        } else if (res.status === 403) {
          window.dispatchEvent(new CustomEvent('auth:forbidden'));
        }
        return res;
      });
    },
    [apiUrl, token],
  );

  const login = useCallback(async (username: string, password: string) => {
    const base = apiUrl.trim().replace(/\/$/, '');
    const res = await fetch(`${base}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Đăng nhập thất bại');
    }
    const data = await res.json();
    localStorage.setItem(TOKEN_KEY, data.access_token);
    const userData: User = data.user;
    localStorage.setItem(USER_KEY, JSON.stringify(userData));
    setToken(data.access_token);
    setUser(userData);
  }, [apiUrl]);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    if (!token) return;
    const base = apiUrl.trim().replace(/\/$/, '');
    fetch(`${base}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then((res) => {
      if (!res.ok) {
        logout();
        return null;
      }
      return res.json();
    }).then((userData) => {
      if (userData) {
        setUser(userData);
        localStorage.setItem(USER_KEY, JSON.stringify(userData));
      }
    }).catch(() => logout());
  }, [token]);

  return (
    <AuthContext.Provider value={{ token, user, isAuthenticated, isAdmin, isStaff, login, logout, apiUrl, setApiUrl, apiFetch }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
