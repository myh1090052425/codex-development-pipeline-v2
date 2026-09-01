# Codex Development Pipeline v2

这是一套给 Codex Desktop 用的开发工作流。

Codex 做长任务时，最容易出问题的是：写代码、跑测试和评审都由同一个会话完成，最后只能靠它自己证明自己没错。

这个项目把三件事拆给不同的 agent，并规定什么时候可以继续、什么时候必须停。

## 它怎么工作

一次任务里只有一个主会话。主会话负责理解目标、安排工作和做最终判断，但不直接改代码。

```text
你
└── 主会话（Coordinator）
    ├── Implementer：唯一可以改代码或测试的 agent
    ├── Verifier：独立运行测试和检查，不负责修复
    └── Reviewer：独立找问题，不负责修复
```

这样做的目的很简单：写代码的人不自己宣布“已经没问题”，主会话也不会一边改代码一边审核自己。

## 安装并开始使用

```bash
git clone https://github.com/myh1090052425/codex-development-pipeline-v2.git
cd codex-development-pipeline-v2
python3 scripts/validate.py
./scripts/install.sh
```

安装器默认写入 `${CODEX_HOME:-$HOME/.codex}`。

它会先记录五个目标文件原本存在还是缺失，并备份已有文件。安装后会重新验证五个 runtime 文件和四个受保护文件。任何步骤失败，都会恢复原文件或原本的缺失状态。

受保护文件是：

```text
~/.codex/skills/development-pipeline/SKILL.md
~/.codex/skills/development-pipeline/agents/openai.yaml
~/.codex/config.toml
~/.codex/AGENTS.md
```

安装后新开一个 Codex 任务，显式调用：

```text
$development-pipeline-v2 <任务描述>
```

这套 Skill 不会自动接管普通任务。

## 一次任务会经历什么

1. **先理解仓库**

   读取项目里的 `AGENTS.md`、现有实现、测试入口、依赖、Git 状态和用户尚未提交的修改。

2. **确认现在到底缺什么**

   Verifier 先检查目标是否已经满足。已经满足的内容保留为回归检查；确实缺失的内容才进入开发。

3. **先建立测试证据**

   新行为需要先有会失败的测试。现有行为已经正确时，就补一个在当前实现上通过、在回归反例上失败的长期测试。不会为了得到失败结果而故意破坏实现。

4. **由唯一 writer 完成修改**

   Implementer 只改事先划定的文件。测试、实现和临时输出都有明确边界。

5. **独立验证**

   Verifier 重新运行目标测试、回归测试、静态检查、类型检查、构建和必要的运行时检查。

6. **独立评审**

   Reviewer 检查正确性、错误处理、数据流、测试覆盖、仓库一致性、复用情况和过度设计。

   安全、迁移、性能、前端、UX 等专项评审只在确实相关时加入。

7. **有问题就整批修复**

   有效问题会合并成一个修复批次，再走测试、修改、验证和评审。这样的候选修复最多三轮；第三轮仍有问题就停止。

## 常见术语

| 术语 | 人话解释 |
| --- | --- |
| `BASELINE` | 修改前先确认哪些目标已经满足，哪些确实需要改 |
| `RED` | 新行为的测试先因正确原因失败 |
| `CHARACTERIZE` | 行为已经正确，只补一个能识别回归的长期测试 |
| `GREEN` / `FIX` | 实现新功能或修复评审问题 |
| `FULL` | 在同一个稳定版本上跑完整验证 |
| finding | Reviewer 提出的具体问题，必须有证据、影响和清除条件 |
| candidate cycle | 只有标记为 `FORM_CANDIDATE` 的 writer 通过全部边界检查后才形成一轮；RED 和 mixed CHARACTERIZE 测试准备不计数 |
| `BLOCKED` | 证据或边界不足，流程停止，不猜测、不绕过 |

## 什么时候会问你

调用一次后，同一目标和架构内的本地可逆工作会自动继续，不会每轮都让你确认。

只有这些情况会重新询问：

- 目标或架构发生实质扩张
- 涉及生产环境、外部系统或真实用户数据
- 涉及凭据、权限或破坏性操作
- 需要修改 Git history 或 index

普通的下一轮修复、重新验证和最终 SHA 不需要重复授权。

## 关于 Full access

Codex 的 subagent 会继承父任务当前的权限模式。因此，本项目不会仅凭 agent TOML 就声称有硬沙盒隔离。

`HARD` 必须实际证明：

- Reviewer 是 read-only
- Implementer 和 Verifier 只有目标根目录的 workspace-write

满足这些条件后，才把边界视为平台强制。

`AUDITED_FULL_ACCESS` 只用于用户已经选择 Full access、任务仍是本地可逆操作、并且当前检查不依赖硬隔离的情况。此模式会把临时目录和缓存定向到仓库内，检查文件清单与受保护文件哈希，并禁止外部系统、凭据、生产操作和高风险 Git 操作。

报告必须明确说明：边界不是 OS 强制，无法证明仓库外绝对零写入。

确实依赖硬隔离的检查不会在 `AUDITED_FULL_ACCESS` 下冒险执行，而是返回 `BLOCKED(capability-unavailable)`。

## 仓库里有什么

```text
agents/                                  三个 custom agent 定义
skills/development-pipeline-v2/          实际安装的 Skill
docs/development-pipeline-v2-spec.md     给维护者看的完整规则
scripts/install.sh                       安装、备份和失败回滚
scripts/validate.py                      不依赖第三方库的静态验证
.github/workflows/validate.yml           GitHub Actions
```

Runtime 始终只有五个文件。README、规范、安装器和 CI 都只是维护工具，不会被安装进 Skill。

## 修改和发布

1. 修改本仓库，不要直接编辑 `~/.codex` 中的安装副本。
2. 运行 `python3 scripts/validate.py`。
3. 如果改了调度、TDD、权限或 finding-loop，补充能证伪新规则的行为测试。
4. 做独立 review，清空 P0-P3。
5. 运行 `./scripts/install.sh`。
6. 提交并推送源码。

仓库不会包含或安装全局 `AGENTS.md`、`config.toml`、v1、本机 backups、sessions、credentials，也不依赖 Superpowers 或 Ponytail。
