import { useEffect, useState } from "react";
import { AlertCircle, Loader2 } from "lucide-react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../App";

export default function AuthCallbackPage() {
  const { refreshUser } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [error, setError] = useState("");

  useEffect(() => {
    async function finishLogin() {
      const callbackError = params.get("error");
      if (callbackError) {
        setError(callbackError);
        return;
      }
      const user = await refreshUser();
      if (user) {
        navigate("/workbench", { replace: true });
      } else {
        setError("登录回调处理失败，请重新登录。");
      }
    }
    void finishLogin();
  }, [navigate, params, refreshUser]);

  return (
    <main className="callback-page">
      <div className={`callback-state ${error ? "failed" : ""}`}>
        {error ? <AlertCircle size={26} /> : <Loader2 size={26} className="spin" />}
        <strong>{error ? "授权失败" : "正在建立登录态"}</strong>
        <span>{error || "正在校验凭据并进入工作台..."}</span>
        {error && (
          <button type="button" onClick={() => navigate("/login", { replace: true })}>
            返回登录
          </button>
        )}
      </div>
    </main>
  );
}
