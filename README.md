# 项目二：内容任务规划 Agent

帮助运营人员在预算与截止时间内完成内容活动方案。支持素材检索、脚本生成、成本估算、方案保存、预算重新规划、失败保留结果和跨运行续跑。

**交付状态：18 项离线测试通过，13/13 离线验收场景通过。智谱模型适配器已接入代码，但本项目尚未运行真实模型；Mock 记录不证明真实 ReAct 决策效果。**

## 最短运行

Python 3.9+，仅标准库；本次本地使用 Python 3.14。解压后进入项目目录：

```bash
cd agent-content-planner
python3 -m src.planner --input data/request.json --output result.json
python3 -m unittest discover -s tests -v
```

默认离线 Mock。`result.json` 包含状态、费用、模拟耗时、任务方案、各步骤状态、工具结果、失败事件及 Trace。`planner.sqlite` 保存成功步骤和最终方案。同一输入与资料重复运行不会重复收费或新增方案。

## 一条命令验证全部场景

```bash
python3 scripts/evaluate.py --mode mock --output examples/my-check
```

13 个用例包括五项必须验收，以及截止时间、重复执行、瞬时失败、保存失败和失败续跑。独立临时数据库保证重复运行测试不会受旧数据污染；每个用例保存输入、实际输出、Trace、断言，另有总报告。

## 可选：智谱真实模型

Mac 当前终端执行：

```bash
zsh scripts/run_live.zsh
```

脚本在本地隐式输入 Key；如果此前将智谱 Key 存在 `OPENROUTER_API_KEY`，会在该脚本内复用为 `ZHIPU_API_KEY`。仅请求智谱普通 API，不请求 OpenRouter。默认 `glm-4-flash-250414`，可通过 `ZHIPU_MODEL` 指定账户可用模型。真实 API 用量与模拟业务预算分开，脚本可能产生实际 API 费用。

默认每场景最多 14 次模型决策，每次请求超时 30 秒；接口失败会停止批量运行并打印脱敏错误。真实证据写入新建的 examples/live-时间戳/。至少需要两条工具观察导致模型调整动作的 live Trace 才能完成真实 ReAct 证明。不要把项目一的真实记录当作项目二证据。

## 失败续跑演示

```bash
python3 -m src.planner --input data/request.json --failure generate_always --db resume.sqlite --output failed.json
python3 -m src.planner --input data/request.json --db resume.sqlite --output resumed.json
```

第一条按预期返回非零退出码，素材检索成功结果仍保存；第二条去掉故障，复用素材继续生成和保存。原失败事件保留，当前步骤状态会更新为成功。首次失败不收生成费，但消耗 1 个模拟分钟。

## 评审入口

- [需求与成功标准](docs/01-requirements.md)
- [流程与设计取舍](docs/02-solution.md)
- [实际评估与限制](docs/03-evaluation.md)
- [AI 辅助说明](docs/04-ai-usage.md)
- [复盘及时间口径](docs/05-retrospective.md)
- [离线验收报告](examples/mock-validation/REPORT.md)
- [测试输出](examples/test-results.txt)

## 提交边界

题号：2。源码包是当前交付物，未创建/推送项目二 GitHub 仓库。原考核仍要求 GitHub URL、最终 commit SHA、私有仓库评审可读。本包 LOCAL_COMMIT.txt 仅标记本地版本，不证明已上传。正式提交前还需真实模型验证和远程交付。
