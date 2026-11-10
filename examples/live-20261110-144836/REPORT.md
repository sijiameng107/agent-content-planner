# live 验收结果

通过 12/13；实际执行 13。

| 用例 | 通过 | 证据 |
|---|---|---|
| normal | True | [输入](normal/input.json) / [实际输出与 Trace](normal/output.json) / [断言](normal/assertions.json) |
| missing_budget | True | [输入](missing_budget/input.json) / [实际输出与 Trace](missing_budget/output.json) / [断言](missing_budget/assertions.json) |
| missing_deadline | True | [输入](missing_deadline/input.json) / [实际输出与 Trace](missing_deadline/output.json) / [断言](missing_deadline/assertions.json) |
| tool_failure | True | [输入](tool_failure/input.json) / [实际输出与 Trace](tool_failure/output.json) / [断言](tool_failure/assertions.json) |
| budget_replan | True | [输入](budget_replan/input.json) / [实际输出与 Trace](budget_replan/output.json) / [断言](budget_replan/assertions.json) |
| budget_impossible | True | [输入](budget_impossible/input.json) / [实际输出与 Trace](budget_impossible/output.json) / [断言](budget_impossible/assertions.json) |
| deadline_impossible | True | [输入](deadline_impossible/input.json) / [实际输出与 Trace](deadline_impossible/output.json) / [断言](deadline_impossible/assertions.json) |
| duplicate_first | True | [输入](duplicate_first/input.json) / [实际输出与 Trace](duplicate_first/output.json) / [断言](duplicate_first/assertions.json) |
| duplicate_repeat | True | [输入](duplicate_repeat/input.json) / [实际输出与 Trace](duplicate_repeat/output.json) / [断言](duplicate_repeat/assertions.json) |
| resume_first | True | [输入](resume_first/input.json) / [实际输出与 Trace](resume_first/output.json) / [断言](resume_first/assertions.json) |
| resume_second | False | [输入](resume_second/input.json) / [实际输出与 Trace](resume_second/output.json) / [断言](resume_second/assertions.json) |
| transient_failure | True | [输入](transient_failure/input.json) / [实际输出与 Trace](transient_failure/output.json) / [断言](transient_failure/assertions.json) |
| save_failure | True | [输入](save_failure/input.json) / [实际输出与 Trace](save_failure/output.json) / [断言](save_failure/assertions.json) |

Mock proves control flow only; live decision evidence requires actual model calls.
