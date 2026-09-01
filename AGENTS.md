# Repository Instructions

- 本仓库是 `development-pipeline-v2` 的源码与维护入口；不要直接修改 `~/.codex` 中的安装副本。
- Runtime source 恰为：
  - `skills/development-pipeline-v2/SKILL.md`
  - `skills/development-pipeline-v2/agents/openai.yaml`
  - `agents/dp-v2-implementer.toml`
  - `agents/dp-v2-reviewer.toml`
  - `agents/dp-v2-verifier.toml`
- Runtime 必须保持 explicit-only、最多 `220` 个非空行和 `24000` bytes；不得向 Skill 目录增加 `references/`、`scripts/` 或其他文件。
- 合同或状态机变更必须同步更新 `docs/development-pipeline-v2-spec.md`，并在验收完成前保持其状态为 `Draft`。
- 每次修改后必须运行 `python3 scripts/validate.py`；涉及调度、TDD、权限或 finding-loop 时还需补充可证伪行为测试和独立 review，P0-P3 清零后才可标记 `Accepted`。
- 安装使用 `./scripts/install.sh`；安装器只允许复制五个 runtime 文件，并必须保留备份与失败回滚能力。
- 不提交本机 `config.toml`、全局 `AGENTS.md`、v1、backups、sessions、credentials 或临时 fixture。
- 不引入 Superpowers 或 Ponytail；需要复用/反过度设计原则时直接维护本仓库现有合同。
