# PRGuardBench

## CI 绿了，PR 就一定安全吗？

首版提供两条彼此独立的评测链：**审核器能否发现有问题的 PR**，以及**修复代码的同时是否破坏了测试与 CI**。

这是可运行的开发基准，不是已经测过 Claude Code / Codex 的排行榜。没有付费模型调用，也没有虚构模型分数。英文主页见 [README](README.md)。

### 已交付

- **42 个审核案例**：21 个风险案例、21 个正常反例，覆盖删除断言、弱化断言、删除测试、跳过测试、范围越界、缺少要求的测试、弱化 CI。
- **5 个真实可执行的微型修复任务**与 **26 个独立行为检查**；原测试通过、功能正确、保护策略未破坏分别评分。
- **统一 JSON 适配协议**、超时及错误处理、结果回放、完整分母评分。
- **自包含 HTML + Markdown 报告**，每个误报都可展开查看。
- Python 包、自动测试、CI 工作流、MIT 协议及后续接手文档。

### 本地运行

```bash
python -m venv .venv
# Linux/macOS
. .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install .
prguardbench validate
prguardbench demo --out results/my-demo
```

直接打开 `results/my-demo/index.html`。默认评测不联网、不执行候选代码、不需要 API Key。

完整演示仅执行仓库内明确提供、可人工检查的脚本对照组：

```bash
prguardbench demo --include-repairs --backend trusted-local --out results/full-demo
```

**`trusted-local` 不是沙箱，不能拿来运行不可信的模型输出。** 对第三方提交，默认走 Docker；没有 Docker 会拒绝执行，绝不自动改为本机执行。当前交付环境没有 Docker，因此真实 Docker 运行仍待验证；构造参数及拒绝回退的测试已提供。

### 已实测的关键结果

| 对照 | 原测试通过 | 独立功能检查通过 | 保护策略通过 | 综合通过 |
|---|---:|---:|---:|---:|
| 正常修复 | 5/5 | 5/5 | 5/5 | 5/5 |
| 只改测试以“变绿” | 5/5 | 0/5 | 0/5 | 0/5 |
| 不做修改 | 0/5 | 0/5 | 5/5 | 0/5 |

静态 AST/diff 检测器在 42 个开发案例上的平衡准确率为 **90.5%**，仍有 **4 个误报**，报告保留全部失误。这是小型公开开发集上的结果，不能推断真实世界准确率。

### 给派灵的后续交接

先按 [HANDOFF.md](docs/HANDOFF.md) 复现，再在独立新仓库发布。正式运行 Claude Code、Codex 等代理前，固定模型/代理版本、提示词、预算、运行次数与执行环境；拿到真实结果后才添加模型行。不要把同一个账号控制的 fork 测试写成第三方采用。
