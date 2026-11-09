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

Mock 模型是确定性测试策略，只验证控制器、工具、预算账本和状态持久化。上述13例均不是实际大模型决策记录。本项目尚无真实模型路径，不能据此宣称已满足真实 ReAct 考核。真实运行入口已提供，会保留失败并输出独立报告，不修改期望值迎合结果。

限制：时间为虚拟时钟；固定关键词检索与事实模板无法衡量真实营销创意质量；失败收费0只是建模假设；业务单位不等于真实 API 费用；所有缺预算/截止案例由输入校验直接拒绝，不调用模型；模型可能选择保守停止或耗尽步数，需 live 验证。持久数据库适合小型 CLI，不是生产级多用户授权系统。
