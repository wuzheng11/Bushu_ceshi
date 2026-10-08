import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { apiFetch } from "./lib/api";
import type { User } from "./types";
import LoginPage from "./pages/LoginPage";
import AuthCallbackPage from "./pages/AuthCallbackPage";
import WorkbenchPage from "./pages/WorkbenchPage";
import AdminConfigPage from "./pages/AdminConfigPage";
import AdminLogsPage from "./pages/AdminLogsPage";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  refreshUser: () => Promise<User | null>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}

function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async (): Promise<User | null> => {
    try {
      const current = await apiFetch<User>("/api/auth/me");
      setUser(current);
      localStorage.setItem("attribution_user", JSON.stringify(current));
      return current;
    } catch {
      setUser(null);
      localStorage.removeItem("attribution_user");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    await apiFetch("/api/auth/logout", { method: "POST" });
    setUser(null);
    localStorage.removeItem("attribution_user");
  }, []);

  useEffect(() => {
    void refreshUser();
  }, []);

  const value = useMemo(
    () => ({ user, loading, refreshUser, logout }),
    [user, loading, refreshUser, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

function Protected({ children, admin = false }: { children: React.ReactNode; admin?: boolean }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) {
    return <div className="page-loader">正在加载...</div>;
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (admin && user.role !== "admin") {
    return <Navigate to="/workbench" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<Navigate to="/workbench" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/login/callback" element={<AuthCallbackPage />} />
        <Route
          path="/workbench"
          element={
            <Protected>
              <WorkbenchPage />
            </Protected>
          }
        />
        <Route
          path="/admin/config"
          element={
            <Protected admin>
              <AdminConfigPage />
            </Protected>
          }
        />
        <Route
          path="/admin/logs"
          element={
            <Protected admin>
              <AdminLogsPage />
            </Protected>
          }
        />
        <Route path="*" element={<Navigate to="/workbench" replace />} />
      </Routes>
    </AuthProvider>
  );
}
