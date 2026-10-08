import { BarChart3, LogIn } from "lucide-react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../App";

export default function LoginPage() {
  const { user, loading } = useAuth();
  if (loading) return <div className="page-loader">正在检查登录状态...</div>;
  if (user) return <Navigate to="/workbench" replace />;

  return (
    <main className="login-page">
      <section className="login-identity">
        <span className="login-kicker">BUSINESS ATTRIBUTION</span>
        <div className="login-logo">
          <BarChart3 size={34} />
        </div>
        <h1>经营归因分析系统</h1>
        <p>从经营现象出发，连续追问、补充证据并形成阶段性结论。</p>
      </section>
      <section className="login-action">
        <div>
          <span>本地授权入口</span>
          <h2>进入分析工作台</h2>
        </div>
        <button
          type="button"
          onClick={() => {
            window.location.href = "/auth/login";
          }}
        >
          <LogIn size={19} />
          使用认证中心登录
        </button>
        <small>演示账号：analyst / analyst123</small>
      </section>
    </main>
  );
}
