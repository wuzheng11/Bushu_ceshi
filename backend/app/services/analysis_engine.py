from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable

from .tools import (
    ConversationFileTool,
    DatabaseQueryTool,
    RuleBasedLLMProvider,
    SafeCommandTool,
    TextSearchTool,
    ToolExecution,
)


EventPublisher = Callable[[str, dict[str, Any]], Awaitable[None]]


@dataclass
class AnalysisContext:
    task_id: int
    conversation_id: int
    user_id: int
    input_text: str
    attachment_paths: list[Path]
    previous_summary: str | None
    config: dict[str, Any]


@dataclass
class AnalysisOutcome:
    scenario: str
    problem_definition: str
    key_metrics: list[dict[str, Any]]
    evidence_list: list[dict[str, Any]]
    conclusion_text: str
    missing_data_text: str
    next_action_text: str
    workspace_files: list[str]


class AnalysisEngine:
    def __init__(self) -> None:
        self.llm_provider = RuleBasedLLMProvider()

    async def run(self, context: AnalysisContext, publish: EventPublisher) -> AnalysisOutcome:
        max_rows = int(context.config.get("max_database_rows", 500))
        db_tool = DatabaseQueryTool(max_rows=max_rows)
        file_tool = ConversationFileTool(context.user_id, context.conversation_id)
        text_tool = TextSearchTool(context.user_id, context.conversation_id)
        command_tool = SafeCommandTool()

        await publish("task_status", {"task_status": "running", "current_step": "识别业务场景"})
        scenario = self._detect_scenario(context.input_text, context.config.get("default_scenario", "auto"))

        if context.config.get("enable_command_tool", True):
            await publish("tool_start", {"tool_name": "command_execution"})
            command_result = command_tool.run("worker_check")
            await self._publish_tool_finish(publish, command_result)

        await publish("task_status", {"task_status": "running", "current_step": "查询经营数据"})
        if scenario == "catalog":
            outcome = await self._run_catalog_analysis(context, db_tool, file_tool, text_tool, publish)
        else:
            outcome = await self._run_customer_analysis(context, db_tool, file_tool, text_tool, publish)

        if context.config.get("enable_llm_placeholder", True):
            await publish("task_status", {"task_status": "running", "current_step": "生成结构化归因结论"})
            generated = self.llm_provider.generate_report(
                {
                    "problem_definition": outcome.problem_definition,
                    "key_metrics": outcome.key_metrics,
                    "evidence_list": outcome.evidence_list,
                    "conclusion_text": outcome.conclusion_text,
                    "missing_data_text": outcome.missing_data_text,
                    "next_action_text": outcome.next_action_text,
                }
            )
            outcome.problem_definition = generated["problem_definition"]
            outcome.key_metrics = generated["key_metrics"]
            outcome.evidence_list = generated["evidence_list"]
            outcome.conclusion_text = generated["conclusion_text"]
            outcome.missing_data_text = generated["missing_data_text"]
            outcome.next_action_text = generated["next_action_text"]

        return outcome

    @staticmethod
    def _detect_scenario(input_text: str, default_scenario: str) -> str:
        customer_keywords = ("客户", "漏斗", "加购", "访问", "下单", "用户行为", "流失")
        catalog_keywords = ("商品", "目录", "类目", "曝光", "点击", "转化率", "sku")
        lowered = input_text.lower()
        customer_score = sum(keyword in lowered for keyword in customer_keywords)
        catalog_score = sum(keyword in lowered for keyword in catalog_keywords)
        if customer_score > catalog_score:
            return "customer"
        if catalog_score > customer_score:
            return "catalog"
        return "customer" if default_scenario == "customer" else "catalog"

    async def _run_catalog_analysis(
        self,
        context: AnalysisContext,
        db_tool: DatabaseQueryTool,
        file_tool: ConversationFileTool,
        text_tool: TextSearchTool,
        publish: EventPublisher,
    ) -> AnalysisOutcome:
        query = """
        SELECT
            c.category_id,
            c.category_name,
            c.attribute_completeness,
            SUM(si.impressions) AS impressions,
            SUM(COALESCE(pc.clicks, 0)) AS clicks,
            SUM(COALESCE(pcv.orders, 0)) AS orders,
            SUM(COALESCE(pcv.gmv, 0)) AS gmv
        FROM category_master c
        JOIN product_master p ON p.category_id = c.category_id
        LEFT JOIN search_impressions si ON si.product_id = p.product_id
        LEFT JOIN product_clicks pc
            ON pc.product_id = p.product_id
            AND pc.click_date = si.impression_date
        LEFT JOIN product_conversions pcv
            ON pcv.product_id = p.product_id
            AND pcv.order_date = si.impression_date
        GROUP BY c.category_id, c.category_name, c.attribute_completeness
        ORDER BY impressions DESC
        """
        await publish("tool_start", {"tool_name": "database_query"})
        result = db_tool.execute(query)
        await self._publish_tool_finish(
            publish,
            result,
            summary_override=f"商品目录聚合查询完成，返回 {len(result.data['rows'])} 个类目",
        )

        rows = result.data["rows"]
        min_impressions = int(context.config.get("min_impressions", 1000))
        low_ctr_threshold = float(context.config.get("low_ctr_threshold", 0.035))
        low_cvr_threshold = float(context.config.get("low_cvr_threshold", 0.025))
        for row in rows:
            impressions = int(row["impressions"] or 0)
            clicks = int(row["clicks"] or 0)
            orders = int(row["orders"] or 0)
            row["ctr"] = clicks / impressions if impressions else 0.0
            row["cvr"] = orders / clicks if clicks else 0.0
        high_traffic = [row for row in rows if int(row["impressions"] or 0) >= min_impressions]
        weak_categories = sorted(
            [row for row in high_traffic if row["ctr"] < low_ctr_threshold or row["cvr"] < low_cvr_threshold],
            key=lambda item: (item["ctr"], item["cvr"]),
        )

        total_impressions = sum(int(row["impressions"] or 0) for row in rows)
        total_clicks = sum(int(row["clicks"] or 0) for row in rows)
        total_orders = sum(int(row["orders"] or 0) for row in rows)
        total_gmv = round(sum(float(row["gmv"] or 0) for row in rows), 2)
        overall_ctr = total_clicks / total_impressions if total_impressions else 0.0
        overall_cvr = total_orders / total_clicks if total_clicks else 0.0

        file_result = file_tool.write_json(
            f"task_{context.task_id}/catalog_metrics.json",
            {"rows": rows, "thresholds": {"ctr": low_ctr_threshold, "cvr": low_cvr_threshold}},
        )
        await publish("tool_start", {"tool_name": "file_write"})
        await self._publish_tool_finish(publish, file_result)
        read_result = file_tool.read_text(f"task_{context.task_id}/catalog_metrics.json")
        await publish("tool_start", {"tool_name": "file_read"})
        await self._publish_tool_finish(publish, read_result, summary_override="中间指标文件回读校验通过")

        search_result = await self._run_text_search(context, text_tool, publish)
        evidence = self._catalog_evidence(weak_categories, search_result)
        weak_names = "、".join(row["category_name"] for row in weak_categories[:3]) or "暂未发现"
        impact_rate = (
            sum(int(row["impressions"] or 0) for row in weak_categories) / total_impressions
            if total_impressions
            else 0.0
        )

        outcome = AnalysisOutcome(
            scenario="catalog",
            problem_definition=(
                f"围绕“{context.input_text.strip()}”分析商品目录中高曝光类目的点击与转化质量，"
                "定位目录结构、类目属性或商品信息导致的经营损失。"
            ),
            key_metrics=[
                {
                    "metric_name": "总曝光量",
                    "metric_value": total_impressions,
                    "metric_unit": "次",
                    "metric_period": "最近30天",
                },
                {
                    "metric_name": "整体点击率",
                    "metric_value": round(overall_ctr * 100, 2),
                    "metric_unit": "%",
                    "metric_period": "最近30天",
                },
                {
                    "metric_name": "整体点击到下单转化率",
                    "metric_value": round(overall_cvr * 100, 2),
                    "metric_unit": "%",
                    "metric_period": "最近30天",
                },
                {
                    "metric_name": "低效类目曝光占比",
                    "metric_value": round(impact_rate * 100, 2),
                    "metric_unit": "%",
                    "metric_period": "最近30天",
                },
                {
                    "metric_name": "样例GMV",
                    "metric_value": total_gmv,
                    "metric_unit": "元",
                    "metric_period": "最近30天",
                },
            ],
            evidence_list=evidence,
            conclusion_text=(
                f"主要问题集中在 {weak_names}。这些类目贡献较高曝光，但点击率低于 "
                f"{low_ctr_threshold * 100:.1f}% 或转化率低于 {low_cvr_threshold * 100:.1f}% 的基线。"
                f"低效类目覆盖约 {impact_rate * 100:.1f}% 的曝光，说明问题不是单一商品，"
                "而是类目入口、属性完整度和搜索承接共同造成。优先修复属性完整度低且点击率弱的类目，"
                "预计比简单增加曝光更能改善整体转化效率。"
            ),
            missing_data_text=(
                "缺少商品主图版本、价格历史、竞品价格、搜索排序位置、库存状态和页面加载时长。"
                "这些数据用于区分目录问题与竞价、季节性、断货等外因。"
            ),
            next_action_text=(
                "1. 对低点击高曝光类目执行标题、主图、价格带和属性完整度的 A/B 测试。\n"
                "2. 将属性完整度低于 80% 的重点商品加入目录治理清单，并设置两周复盘节点。\n"
                "3. 补充搜索排序位置和竞品价格，验证低点击是否由排序下移或价格劣势导致。\n"
                "4. 对修复后的类目跟踪点击率、转化率和 GMV，避免只看曝光增长。"
            ),
            workspace_files=[str(file_result.data["file_path"])],
        )
        return outcome

    async def _run_customer_analysis(
        self,
        context: AnalysisContext,
        db_tool: DatabaseQueryTool,
        file_tool: ConversationFileTool,
        text_tool: TextSearchTool,
        publish: EventPublisher,
    ) -> AnalysisOutcome:
        query = """
        SELECT
            u.channel,
            u.city,
            COUNT(DISTINCT v.user_id) AS visitors,
            COUNT(DISTINCT a.user_id) AS cart_users,
            COUNT(DISTINCT o.user_id) AS order_users
        FROM business_users u
        LEFT JOIN visit_events v ON v.user_id = u.user_id
        LEFT JOIN add_cart_events a ON a.user_id = u.user_id
        LEFT JOIN order_events o ON o.user_id = u.user_id AND o.status = 'paid'
        GROUP BY u.channel, u.city
        ORDER BY visitors DESC
        """
        await publish("tool_start", {"tool_name": "database_query"})
        result = db_tool.execute(query)
        await self._publish_tool_finish(
            publish,
            result,
            summary_override=f"客户行为漏斗查询完成，返回 {len(result.data['rows'])} 个渠道/城市分组",
        )
        rows = result.data["rows"]
        for row in rows:
            visitors = int(row["visitors"] or 0)
            cart_users = int(row["cart_users"] or 0)
            order_users = int(row["order_users"] or 0)
            row["visit_to_cart"] = cart_users / visitors if visitors else 0.0
            row["cart_to_order"] = order_users / cart_users if cart_users else 0.0
            row["visit_to_order"] = order_users / visitors if visitors else 0.0

        visitors = sum(int(row["visitors"] or 0) for row in rows)
        cart_users = sum(int(row["cart_users"] or 0) for row in rows)
        order_users = sum(int(row["order_users"] or 0) for row in rows)
        visit_to_cart = cart_users / visitors if visitors else 0.0
        cart_to_order = order_users / cart_users if cart_users else 0.0
        overall = order_users / visitors if visitors else 0.0
        weak_groups = sorted(
            [row for row in rows if row["visit_to_cart"] < 0.45 or row["cart_to_order"] < 0.35],
            key=lambda item: (item["cart_to_order"], item["visit_to_cart"]),
        )
        stage_loss = (
            "访问到加购"
            if (1 - visit_to_cart) > (1 - cart_to_order)
            else "加购到下单"
        )

        file_result = file_tool.write_json(
            f"task_{context.task_id}/customer_funnel.json",
            {
                "rows": rows,
                "overall": {
                    "visitors": visitors,
                    "cart_users": cart_users,
                    "order_users": order_users,
                    "visit_to_cart": visit_to_cart,
                    "cart_to_order": cart_to_order,
                    "visit_to_order": overall,
                },
            },
        )
        await publish("tool_start", {"tool_name": "file_write"})
        await self._publish_tool_finish(publish, file_result)
        read_result = file_tool.read_text(f"task_{context.task_id}/customer_funnel.json")
        await publish("tool_start", {"tool_name": "file_read"})
        await self._publish_tool_finish(publish, read_result, summary_override="客户漏斗中间文件回读校验通过")

        search_result = await self._run_text_search(context, text_tool, publish)
        evidence = self._customer_evidence(rows, search_result)
        weakest_groups = "、".join(
            f"{row['channel']}/{row['city']}" for row in weak_groups[:3]
        ) or "暂未发现"

        outcome = AnalysisOutcome(
            scenario="customer",
            problem_definition=(
                f"围绕“{context.input_text.strip()}”分析访问、加购、下单三阶段用户转化，"
                "识别主要流失环节及渠道、城市分群差异。"
            ),
            key_metrics=[
                {
                    "metric_name": "访问用户数",
                    "metric_value": visitors,
                    "metric_unit": "人",
                    "metric_period": "最近30天",
                },
                {
                    "metric_name": "访问到加购率",
                    "metric_value": round(visit_to_cart * 100, 2),
                    "metric_unit": "%",
                    "metric_period": "最近30天",
                },
                {
                    "metric_name": "加购到下单率",
                    "metric_value": round(cart_to_order * 100, 2),
                    "metric_unit": "%",
                    "metric_period": "最近30天",
                },
                {
                    "metric_name": "访问到下单率",
                    "metric_value": round(overall * 100, 2),
                    "metric_unit": "%",
                    "metric_period": "最近30天",
                },
                {
                    "metric_name": "待优化分群数",
                    "metric_value": len(weak_groups),
                    "metric_unit": "个",
                    "metric_period": "最近30天",
                },
            ],
            evidence_list=evidence,
            conclusion_text=(
                f"整体最大流失发生在{stage_loss}。访问到加购率为 {visit_to_cart * 100:.1f}%，"
                f"加购到下单率为 {cart_to_order * 100:.1f}%。表现较弱的分群为 {weakest_groups}，"
                "其中加购到下单环节对价格敏感、履约成本和支付体验更敏感。建议先处理弱分群的运费展示、"
                "优惠门槛、库存与结算步骤问题，再评估流量质量问题。"
            ),
            missing_data_text=(
                "缺少优惠券领取与核销、运费金额、库存可售状态、页面停留时长、支付失败原因和退款记录。"
                "现有数据可以定位流失位置，但不足以单独证明价格或履约是唯一原因。"
            ),
            next_action_text=(
                "1. 对弱转化分群上线包邮门槛提示或阶梯优惠，进行两周 A/B 测试。\n"
                "2. 补充结算页埋点和支付失败原因，识别加购后未下单的页面级阻力。\n"
                "3. 按渠道拆分新老客和价格敏感度，避免将流量质量问题误判为商品问题。\n"
                "4. 对高访问低加购分群优化商品详情、评价内容和推荐相关性。"
            ),
            workspace_files=[str(file_result.data["file_path"])],
        )
        return outcome

    async def _run_text_search(
        self,
        context: AnalysisContext,
        text_tool: TextSearchTool,
        publish: EventPublisher,
    ) -> ToolExecution:
        await publish("tool_start", {"tool_name": "text_search"})
        search_result = text_tool.search(context.input_text, context.attachment_paths)
        await self._publish_tool_finish(publish, search_result)
        return search_result

    @staticmethod
    async def _publish_tool_finish(
        publish: EventPublisher,
        result: ToolExecution,
        summary_override: str | None = None,
    ) -> None:
        await publish(
            "tool_finish",
            {
                "tool_name": result.tool_name,
                "tool_result_summary": summary_override or result.summary,
                "tool_status": result.status,
            },
        )

    @staticmethod
    def _catalog_evidence(
        weak_categories: list[dict[str, Any]],
        search_result: ToolExecution,
    ) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        for row in weak_categories[:4]:
            evidence.append(
                {
                    "source_type": "database",
                    "source_name": "category_master / search_impressions / product_clicks",
                    "evidence_text": (
                        f"{row['category_name']}曝光{int(row['impressions'] or 0)}次，"
                        f"点击率{float(row['ctr']) * 100:.2f}%，"
                        f"点击到下单率{float(row['cvr']) * 100:.2f}%，"
                        f"属性完整度{float(row['attribute_completeness']) * 100:.0f}%。"
                    ),
                    "related_metric": "点击率、转化率、属性完整度",
                    "confidence": 0.86,
                }
            )
        for match in search_result.data.get("matches", [])[:2]:
            evidence.append(
                {
                    "source_type": match["source_type"],
                    "source_name": match["source_name"],
                    "evidence_text": match["excerpt"][:220],
                    "related_metric": "目录优化判断规则",
                    "confidence": 0.72,
                }
            )
        return evidence

    @staticmethod
    def _customer_evidence(
        rows: list[dict[str, Any]],
        search_result: ToolExecution,
    ) -> list[dict[str, Any]]:
        weakest = sorted(rows, key=lambda item: (item["cart_to_order"], item["visit_to_cart"]))[:4]
        evidence: list[dict[str, Any]] = []
        for row in weakest:
            evidence.append(
                {
                    "source_type": "database",
                    "source_name": "visit_events / add_cart_events / order_events",
                    "evidence_text": (
                        f"{row['channel']}/{row['city']}访问{int(row['visitors'] or 0)}人，"
                        f"访问到加购率{float(row['visit_to_cart']) * 100:.2f}%，"
                        f"加购到下单率{float(row['cart_to_order']) * 100:.2f}%。"
                    ),
                    "related_metric": "访问到加购率、加购到下单率",
                    "confidence": 0.84,
                }
            )
        for match in search_result.data.get("matches", [])[:2]:
            evidence.append(
                {
                    "source_type": match["source_type"],
                    "source_name": match["source_name"],
                    "evidence_text": match["excerpt"][:220],
                    "related_metric": "漏斗归因判断规则",
                    "confidence": 0.72,
                }
            )
        return evidence
