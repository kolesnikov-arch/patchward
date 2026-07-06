# patchward

**[🇺🇸 English](README.md) | 🇨🇳 简体中文**

**面向 AI 编码智能体的判决层 (verdict layer)——让智能体无法悄悄交付一个坏掉的修复。**

> **📊 首次留出集 (held-out) 评测结果已发布：[RESULTS_zh.md](RESULTS_zh.md)** — 在一个冻结的、
> 预注册的 50 任务集上，同一个模型在无门控时**静默交付了 17/50** 个错误修复，有门控时为
> **0/50**。每个数字都可以从 [`evaluation-artifacts/`](evaluation-artifacts/) 复算。
> 强化后的引擎按设计保持私有；这里公开的是**证据**，供你亲自核验这些论断。

---

## 基准测量能力，CI 需要的是信任

AI 编码智能体的评分标准是**解决率**——修了多少个 bug。那是**能力 (capability)**，也是绝大多数
智能体基准所测量的。而真正决定你能否让一个智能体进入 CI 的，是另一个少有人报告的数字：
**误受率 (false-accept rate)**——智能体多久会*自信地交付*一个看起来正确、实则悄悄出错的修复。

更糟的是，智能体在给自己的作业打分：

> 智能体写下修复 → 智能体为它写一个测试 → 测试通过
> （它编码的是智能体*自己*的误解）→ 智能体报告成功。

绿色对勾，隐藏缺陷。在基准上这看起来是一次胜利；在生产环境里，它是高负载下才引爆的回归。

## 方法：把生成与裁决分离

概率性的 LLM 负责**提出**；一个独立的、确定性的判决层负责**决定**。作出判决的是检查本身，
而不是智能体自己——而且诚实的结果有三种，不是二元的通过/失败：

- 🟢 **已验证 (Verified)** —— 经独立确认（例如：既有测试在隔离容器中通过；变更在声明范围内
  且未引入回归）。
- 🟡 **未验证 (Unverified / Needs review)** —— 看似合理，但未能独立确认 → 标记给人工复核。
  系统诚实地说出它*没能*检查的部分，而不是盖橡皮图章。
- 🔴 **已拦截 (Blocked)** —— 被某个门控捕获（修改超出声明范围、检查未通过、引入回归）。

关键在于**可问责性 (accountability)**：把一个无法问责的 AI 补丁，变成一个携带判决与审计
轨迹的补丁——无论测试能否执行。

## 判决如何形成

判决由独立的、确定性的检查作出——覆盖**范围 (scope)**、**证据 (evidence)** 与
**回归 (regression)**——而不是由智能体作出。其中大多数检查不需要执行代码，因此可以离线、
在物理隔离环境、对任何语言工作；当运行时可用时，隔离的测试运行是一层额外的确认。

这背后的推理——为什么独立判决优于智能体的自我报告、为什么决策是三态而非二态——记录在
配套的[判决层框架（中文版）](https://github.com/kolesnikov-arch/verdict-layer-framework/blob/main/README_zh.md)中
（已抽象化，剥离了实现与工具名）。实现这一切的、经过调校的具体引擎保持私有。

## 什么是公开的——什么不是

**公开：**
- 概念与测量方法论；
- **[RESULTS_zh.md](RESULTS_zh.md)** —— 留出集评测结果：标题计数、精确置信区间、完整的
  处置表、悲观敏感性行、每个误拒 (false-reject) 及其根因、运行完整性日志；
- **[预注册计分契约](PREREGISTRATION_zh.md)** —— 计分规则、报告承诺，以及对尖锐质疑的回答，
  **在结果存在之前即已提交并加盖日期**——因此规则不可能围绕结果拟合；
- **[当前范围与局限](CURRENT_SCOPE_AND_LIMITATIONS_zh.md)** —— 这项测量能与不能说明什么
  （以诚实为构造前提）；
- **[`evaluation-artifacts/`](evaluation-artifacts/)** —— 可复现的证明工具包：两臂的预测
  （与被评测时逐字节一致）、原始的逐任务计分报告、配对结果表、带随机种子的任务选取，以及
  一个仅用标准库、可复算每个标题数字的脚本（目录内文档为英文）；
- 判决逻辑的**交互式模拟**（在[配套仓库](https://github.com/kolesnikov-arch/verdict-layer-framework)中）。

**按设计保持私有：** 经过调校的引擎——门控、提示词，以及它们赖以调校的失败记忆语料库。
从数百次真实运行中提炼出的这份调校，*就是*这项工作本身。我们开放**证据**，而非**引擎**——
论断可以被核验，而护城河不必交出。

## 状态

**评测 #1 已发布（2026-07-05）：[RESULTS_zh.md](RESULTS_zh.md)。** 计分规则在结果存在之前
即已预注册（[PREREGISTRATION_zh.md](PREREGISTRATION_zh.md)，2026-07-03），每个数字都可以从
[`evaluation-artifacts/`](evaluation-artifacts/) 复算——诚实优先于宣传，是构造性的。
概念与信任论点见配套仓库：
[verdict-layer-framework](https://github.com/kolesnikov-arch/verdict-layer-framework/blob/main/README_zh.md)。

评测过程中的实地笔记（英文通讯）：
[Trust in AI Delivery](https://dmitriykolesnikov.substack.com)。

## 许可

概念、文档与结果：**CC BY-NC 4.0**（与
[判决层框架](https://github.com/kolesnikov-arch/verdict-layer-framework)一致）。
演示/示例代码（添加后）：MIT。见 [LICENSE](LICENSE)。
