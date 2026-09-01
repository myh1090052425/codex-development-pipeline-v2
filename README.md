# Codex Development Pipeline v2

适用于 Codex Desktop 的显式、多 agent、证据门禁开发流水线。

当前版本已于 2026-09-01 完成 bootstrap 验收。运行时只有五个文件，必须通过 `$development-pipeline-v2` 显式调用，不会自动接管普通任务。

## 核心约束

- 当前 main session 是唯一 Coordinator，负责冻结边界、调度、核验证据和报告，但不写 candidate、tests 或 fixes。
- `dp-v2-implementer` 是唯一逻辑 writer；`dp-v2-verifier` 独立执行 BASELINE、RED、FULL；`dp-v2-reviewer` 独立评审。
- 支持 strict batch RED、passing CHARACTERIZE + negative counterfactual、完整 FULL、P0-P3 清零和最多三个 candidate cycles。
- 同一 scope/architecture 内的本地可逆闭环一次授权，不逐轮询问。
- 复用顺序为 existing implementation、existing dependency、stdlib/platform、最小新增。
- 不依赖 Superpowers 或 Ponytail。

## 权限模型

- `HARD`：只有实际 child sandbox 与声明一致时，才声称平台强制 read-only/workspace-write。
- `AUDITED_FULL_ACCESS`：父任务使用 Full access 时，依靠 logical role boundary、sanitized env、tree manifest 和 protected hashes 审计；明确报告边界并非 OS 强制，无法证明 root 外零写。
- 必须依赖硬隔离的检查在 `AUDITED_FULL_ACCESS` 下返回 `BLOCKED(capability-unavailable)`。

## 目录

```text
agents/                                  三个 custom agent 定义
skills/development-pipeline-v2/          Skill 与 Desktop metadata
docs/development-pipeline-v2-spec.md     Accepted 规范
scripts/install.sh                       安装、备份和失败回滚
scripts/validate.py                      stdlib-only 静态验证
.github/workflows/validate.yml           GitHub Actions
```

## 验证

```bash
python3 scripts/validate.py
```

验证内容包括：exact-five runtime、frontmatter、explicit-only、TOML 角色、mode/status 合同、关键状态门、`93 NF / 24000 bytes` 预算上限，以及 Accepted 规范。

## 安装

```bash
./scripts/install.sh
```

默认安装到 `${CODEX_HOME:-$HOME/.codex}`。安装器会：

1. 验证源码。
2. 在 `$CODEX_HOME/backups/` 创建权限为 `0700` 的时间戳备份。
3. 只安装五个 runtime 文件。
4. 验证安装结果及 protected inputs。
5. 任一步失败时恢复原始文件或原始 absence。

安装后新开一个 Codex 任务，显式调用：

```text
$development-pipeline-v2 <任务描述>
```

## 维护流程

1. 只修改本仓库源码，不直接编辑 `~/.codex` 中的安装副本。
2. 运行 `python3 scripts/validate.py`。
3. 对状态机或角色合同变更补充行为 fixture，并进行独立 review。
4. P0-P3 清零后运行 `./scripts/install.sh`。
5. 提交并推送源码；不要提交本机备份、配置、全局 `AGENTS.md` 或凭据。

## 受保护边界

本仓库不包含也不会安装：

- 全局 `~/.codex/AGENTS.md`
- `~/.codex/config.toml`
- development-pipeline v1
- 本机 backups、sessions 或 credentials
