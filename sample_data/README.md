# 示例数据说明

## 场景 A：商品目录优化

表：

- `category_master`
- `product_master`
- `search_impressions`
- `product_clicks`
- `product_conversions`

演示问题：

> 请分析最近 30 天商品目录优化问题。重点检查高曝光低点击类目、类目属性完整度与转化变化，并给出下一步动作。

预期工具路径：

1. 场景识别为 `catalog`。
2. 执行类目级曝光、点击、订单和 GMV 聚合 SQL。
3. 写入并回读 `catalog_metrics.json`。
4. 检索目录运营手册和会话附件。
5. 输出六段式报告并导出 Markdown。

预期结论：家居收纳、办公文具、美妆个护存在高曝光低点击或低转化问题，其中家居收纳属性完整度和点击率均偏低。

## 场景 B：客户行为分析

表：

- `business_users`
- `visit_events`
- `add_cart_events`
- `order_events`

演示问题：

> 请分析最近 30 天客户行为漏斗，定位访问到加购、加购到下单的主要流失环节和用户分群差异。

预期工具路径：

1. 场景识别为 `customer`。
2. 执行渠道、城市、访问、加购、付费订单聚合 SQL。
3. 写入并回读 `customer_funnel.json`。
4. 检索漏斗运营手册和会话附件。
5. 输出六段式报告并导出 Markdown。

预期结论：整体加购到下单流失最明显，社交渠道/北京和自然流量/上海的加购后下单率偏低。
