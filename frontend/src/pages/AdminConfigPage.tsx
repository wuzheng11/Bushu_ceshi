import { useEffect, useState } from "react";
import { Database, RefreshCw, Save, ServerCog, Settings2 } from "lucide-react";
import AppHeader from "../components/AppHeader";
import { apiFetch, formatDateTime } from "../lib/api";
import type { ConfigItem } from "../types";

interface DataSource {
  id: number;
  name: string;
  dialect: "mysql" | "sqlite" | "postgresql";
  connection_url: string;
  status: "active" | "disabled";
  updated_at: string;
}

export default function AdminConfigPage() {
  const [tab, setTab] = useState<"system" | "datasource">("system");
  const [configs, setConfigs] = useState<ConfigItem[]>([]);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");
  const [sources, setSources] = useState<DataSource[]>([]);
  const [sourceDraft, setSourceDraft] = useState({
    name: "",
    dialect: "mysql" as "mysql" | "sqlite" | "postgresql",
    connection_url: "",
    status: "active" as "active" | "disabled",
  });

  async function loadConfigs() {
    const items = await apiFetch<ConfigItem[]>("/api/admin/configs");
    setConfigs(items);
    setDraft(Object.fromEntries(items.map((item) => [item.config_key, item.config_value])));
  }

  async function loadSources() {
    setSources(await apiFetch<DataSource[]>("/api/admin/data-sources"));
  }

  useEffect(() => {
    void loadConfigs();
    void loadSources();
  }, []);

  async function saveConfig(item: ConfigItem) {
    await apiFetch(`/api/admin/configs/${encodeURIComponent(item.config_key)}`, {
      method: "PUT",
      body: JSON.stringify({
        config_value: draft[item.config_key],
        config_group: item.config_group,
      }),
    });
    setMessage(`已保存 ${item.config_key}`);
    await loadConfigs();
  }

  async function reloadConfig() {
    const response = await apiFetch<{ status: string; message: string }>("/api/admin/reload", {
      method: "POST",
    });
    setMessage(response.message);
    await loadConfigs();
  }

  async function createSource() {
    await apiFetch("/api/admin/data-sources", {
      method: "POST",
      body: JSON.stringify(sourceDraft),
    });
    setSourceDraft({ name: "", dialect: "mysql", connection_url: "", status: "active" });
    await loadSources();
  }

  async function testSource(id: number) {
    const response = await apiFetch<{ status: string; message: string }>(
      `/api/admin/data-sources/${id}/test`,
      { method: "POST" },
    );
    setMessage(response.message);
  }

  const groups = Array.from(new Set(configs.map((item) => item.config_group)));

  return (
    <div className="app-shell">
      <AppHeader />
      <main className="admin-page">
        <header className="admin-titlebar">
          <div>
            <span>系统管理</span>
            <h1>配置与数据源</h1>
          </div>
          <button className="command-button" type="button" onClick={() => void reloadConfig()}>
            <RefreshCw size={17} />
            热更新配置
          </button>
        </header>
        {message && <div className="admin-message">{message}</div>}
        <div className="admin-tabs">
          <button
            type="button"
            className={tab === "system" ? "active" : ""}
            onClick={() => setTab("system")}
          >
            <Settings2 size={16} />
            系统配置
          </button>
          <button
            type="button"
            className={tab === "datasource" ? "active" : ""}
            onClick={() => setTab("datasource")}
          >
            <Database size={16} />
            数据源连接
          </button>
        </div>
        {tab === "system" ? (
          <div className="config-groups">
            {groups.map((group) => (
              <section className="config-group" key={group}>
                <h2>{group}</h2>
                <div className="config-table">
                  {configs
                    .filter((item) => item.config_group === group)
                    .map((item) => (
                      <div className="config-row" key={item.config_key}>
                        <div>
                          <strong>{item.config_key}</strong>
                          <span>更新于 {formatDateTime(item.updated_at)}</span>
                        </div>
                        <input
                          value={draft[item.config_key] ?? ""}
                          onChange={(event) =>
                            setDraft((current) => ({
                              ...current,
                              [item.config_key]: event.target.value,
                            }))
                          }
                        />
                        <button type="button" title="保存配置" onClick={() => void saveConfig(item)}>
                          <Save size={16} />
                        </button>
                      </div>
                    ))}
                </div>
              </section>
            ))}
          </div>
        ) : (
          <div className="source-layout">
            <section className="source-list">
              <h2>已配置数据源</h2>
              {sources.map((source) => (
                <div className="source-row" key={source.id}>
                  <span className="source-icon">
                    <ServerCog size={18} />
                  </span>
                  <div>
                    <strong>{source.name}</strong>
                    <span>{source.dialect} · {source.status}</span>
                    <small>{source.connection_url}</small>
                  </div>
                  <button type="button" onClick={() => void testSource(source.id)}>
                    测试
                  </button>
                </div>
              ))}
            </section>
            <section className="source-form">
              <h2>新增连接</h2>
              <label>
                名称
                <input
                  value={sourceDraft.name}
                  onChange={(event) =>
                    setSourceDraft((current) => ({ ...current, name: event.target.value }))
                  }
                />
              </label>
              <label>
                类型
                <select
                  value={sourceDraft.dialect}
                  onChange={(event) =>
                    setSourceDraft((current) => ({
                      ...current,
                      dialect: event.target.value as "mysql" | "sqlite" | "postgresql",
                    }))
                  }
                >
                  <option value="mysql">MySQL</option>
                  <option value="sqlite">SQLite</option>
                  <option value="postgresql">PostgreSQL</option>
                </select>
              </label>
              <label>
                连接字符串
                <input
                  value={sourceDraft.connection_url}
                  placeholder="mysql+pymysql://root:password@127.0.0.1:3306/business_attribution_demo?charset=utf8mb4"
                  onChange={(event) =>
                    setSourceDraft((current) => ({
                      ...current,
                      connection_url: event.target.value,
                    }))
                  }
                />
              </label>
              <button
                className="command-button"
                type="button"
                disabled={!sourceDraft.name || !sourceDraft.connection_url}
                onClick={() => void createSource()}
              >
                保存数据源
              </button>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}
