# 实际评估

本次执行：18 项离线测试通过，13/13 离线验收通过。运行命令：`python3 -m unittest discover -s tests -v`；`python3 scripts/evaluate.py --mode mock --output examples/mock-validation`。

[测试输出](../examples/test-results.txt)；[总报告](../examples/mock-validation/REPORT.md)；[结构化汇总](../examples/mock-validation/summary.json)。每个用例目录包含 input.json、output.json（完整 Trace 与持久状态）、assertions.json，资料见 [catalog](../data/catalog.json)。

| 验收点 | 对应实际输出与 Trace |
|---|---|
| 正常 | [normal](../examples/mock-validation/normal/output.json) |
| 缺预算/截止 | [missing_budget](../examples/mock-validation/missing_budget/output.json)、[missing_deadline](../examples/mock-validation/missing_deadline/output.json) |
| 工具失败 | [tool_failure](../examples/mock-validation/tool_failure/output.json)、[save_failure](../examples/mock-validation/save_failure/output.json) |
| 超预算重规划 | [budget_replan](../examples/mock-validation/budget_replan/output.json)：估12不可行，再估8、生成保存 |
| 不可行预算/时间 | [budget_impossible](../examples/mock-validation/budget_impossible/output.json)、[deadline_impossible](../examples/mock-validation/deadline_impossible/output.json) |
| 重复 | [duplicate_first](../examples/mock-validation/duplicate_first/output.json)、[duplicate_repeat](../examples/mock-validation/duplicate_repeat/output.json) |
| 失败续跑 | [resume_first](../examples/mock-validation/resume_first/output.json)、[resume_second](../examples/mock-validation/resume_second/output.json) |
| 瞬时失败恢复 | [transient_failure](../examples/mock-validation/transient_failure/output.json) |

Mock 模型是确定性测试策略，只验证控制器、工具、预算账本和状态持久化。上述13例均不是实际大模型决策记录。真实模型路径见下方本轮报告。真实运行入口已提供，会保留失败并输出独立报告，不修改期望值迎合结果。

限制：时间为虚拟时钟；固定关键词检索与事实模板无法衡量真实营销创意质量；失败收费0只是建模假设；业务单位不等于真实 API 费用；所有缺预算/截止案例由输入校验直接拒绝，不调用模型；模型可能选择保守停止或耗尽步数，需 live 验证。持久数据库适合小型 CLI，不是生产级多用户授权系统。

## 2026-11-10 真实验收

[完整报告](../examples/live-20261110-144836/REPORT.md)。2026-11-10 真实智谱运行 12/13 通过。

[budget_replan](../examples/live-20261110-144836/budget_replan/output.json) 观察到 12 超预算后改选 8 并保存。[budget_impossible](../examples/live-20261110-144836/budget_impossible/output.json) 在预算不可行时结束并返回未完成。

唯一未通过的是加分项 [resume_second](../examples/live-20261110-144836/resume_second/output.json)。检索状态与账本保留，续跑生成脚本后模型提前调用 finish，方案没有保存。已保留原始断言和失败 Trace。
