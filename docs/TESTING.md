# 测试与验收说明

## 自动化测试

在项目根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m backend.app.seed
.\.venv\Scripts\python.exe -m pytest
```

覆盖内容：

| 用例 | 验证点 |
| --- | --- |
| OAuth 授权码流程 | 授权页、用户密码、授权码、token 交换、JWT 用户信息 |
| 未登录访问 | 业务接口返回 `401` |
| 会话和附件 | 创建、上传、解析、下载、发送消息、历史查询、删除级联 |
| 商品目录分析 | SQL 聚合、五个指标、证据、六段报告、Markdown 下载 |
| 客户行为分析 | 漏斗指标、渠道分群、主要流失环节、下一步动作 |
| WebSocket | 单次 token、连接成功、ping/pong |
| 配置热更新 | 修改配置、调用 reload、即时读取新值 |

当前验收结果：

```text
7 passed, 1 warning
```

## 真实进程冒烟测试

启动认证中心和后端：

```powershell
.\.venv\Scripts\python.exe scripts\run_services.py
```

新终端执行：

```powershell
.\.venv\Scripts\python.exe scripts\smoke_live.py
```

该脚本会真实执行：

1. 请求 `GET /auth/login`。
2. 打开认证中心授权页。
3. 提交 `analyst / analyst123`。
4. 获取授权码并回调后端。
5. 使用 JWT Cookie 请求用户信息。
6. 创建会话并发送商品目录分析问题。
7. 轮询任务直到 `success`。
8. 读取五项指标和多条证据。
9. 创建 WebSocket token、连接并接收回放事件。

预期关键输出：

```json
{
  "status": "ok",
  "user": "analyst",
  "task_status": "success",
  "key_metrics": 5,
  "evidence_count": 5,
  "websocket_events": [
    "done",
    "message_delta",
    "message_start",
    "result_ready",
    "task_status",
    "tool_finish",
    "tool_start"
  ]
}
```

## 前端构建验收

```powershell
cd frontend
npm install
npm run build
```

预期：

```text
vite build ... built successfully
```

## 手工操作流程

1. 启动认证中心、后端和前端。
2. 访问 `http://localhost:5173`。
3. 点击“使用认证中心登录”。
4. 输入 `analyst / analyst123`，点击“同意授权并登录”。
5. 回调页自动进入工作台。
6. 点击左上角 `+` 新建会话。
7. 右侧上传一份 CSV、TXT、JSON 或 Markdown 文件。
8. 勾选附件，在底部输入问题并发送。
9. 观察任务区的状态变化和工具执行过程。
10. 任务完成后查看六部分结构化结果。
11. 点击结果区的复制、保存和导出按钮。
12. 在附件区点击下载图标验证附件下载。
13. 切换旧会话并继续追问。
14. 使用 `admin / admin123` 登录，进入配置和日志页面。
15. 修改 `analysis.low_ctr_threshold` 后点击“热更新配置”。

## 两个完整分析场景

### 场景 A：商品目录优化

输入：

```text
请分析最近 30 天商品目录优化问题。重点检查高曝光低点击类目、类目属性完整度与转化变化，并给出下一步动作。
```

预期过程：

1. 场景识别为 `catalog`。
2. 调用安全命令工具。
3. 调用数据库查询工具聚合类目、曝光、点击、订单和 GMV。
4. 写入并回读 `workspace/{user_id}/{conversation_id}/task_{task_id}/catalog_metrics.json`。
5. 检索内置商品目录运营知识。
6. 推送 `message_delta`、`result_ready` 和 `done`。

预期结果：

- 发现家居收纳、办公文具、美妆个护的入口效率问题。
- 家居收纳属性完整度约 `55%`，点击率低于阈值。
- 美妆个护点击到下单率低于阈值。
- 建议优化标题、主图、价格带、属性完整度并执行 A/B 测试。

导出文件：

```text
exports/{user_id}/{conversation_id}/task_{task_id}_result.md
```

### 场景 B：客户行为分析

输入：

```text
请分析最近 30 天客户行为漏斗，定位访问到加购、加购到下单的主要流失环节和用户分群差异。
```

预期过程：

1. 场景识别为 `customer`。
2. 按渠道和城市聚合访问、加购、付费下单人数。
3. 写入并回读 `customer_funnel.json`。
4. 检索客户转化漏斗知识。
5. 输出六段式结果。

预期结果：

- 社交/北京和自然流量/上海的加购后下单表现偏弱。
- 广告渠道的部分访问未进入加购。
- 建议测试包邮门槛、补充结算埋点、拆分新老客。

## 测试截图清单

建议提交前截取以下 10 张图：

| 编号 | 截图内容 | 应体现 |
| --- | --- | --- |
| 01 | 登录入口 | 授权登录按钮 |
| 02 | 认证中心 | 演示账号和授权按钮 |
| 03 | 登录回调 | 建立登录态后自动进入工作台 |
| 04 | 空工作台 | 三栏布局和两个示例问题 |
| 05 | 附件上传 | 文件名、大小、类型、时间、解析状态 |
| 06 | 商品目录实时任务 | 运行步骤、SQL 和文件工具 |
| 07 | 商品目录结果 | 六部分结构和五项关键指标 |
| 08 | 客户行为结果 | 漏斗指标、渠道分群和结论 |
| 09 | 结果导出 | 导出的 Markdown 文件 |
| 10 | 管理员页面 | 配置热更新、数据源连接和运行日志 |
