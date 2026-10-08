import {
  BarChart3,
  LogOut,
  MessageSquareText,
  ScrollText,
  Settings2,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../App";

export default function AppHeader() {
  const { user, logout } = useAuth();

  return (
    <header className="app-header">
      <div className="brand-lockup">
        <span className="brand-mark">
          <BarChart3 size={20} strokeWidth={2.2} />
        </span>
        <div>
          <strong>经营归因分析</strong>
          <span>Attribution workspace</span>
        </div>
      </div>
      <nav className="header-nav" aria-label="主导航">
        <NavLink to="/workbench">
          <MessageSquareText size={17} />
          工作台
        </NavLink>
        {user?.role === "admin" && (
          <>
            <NavLink to="/admin/config">
              <Settings2 size={17} />
              配置
            </NavLink>
            <NavLink to="/admin/logs">
              <ScrollText size={17} />
              日志
            </NavLink>
          </>
        )}
      </nav>
      <div className="user-area">
        <div className="user-avatar">{user?.display_name?.slice(0, 1) || "用"}</div>
        <div className="user-meta">
          <strong>{user?.display_name}</strong>
          <span>{user?.role === "admin" ? "系统管理员" : "分析用户"}</span>
        </div>
        <button className="icon-button" type="button" onClick={() => void logout()} title="退出登录">
          <LogOut size={18} />
        </button>
      </div>
    </header>
  );
}
