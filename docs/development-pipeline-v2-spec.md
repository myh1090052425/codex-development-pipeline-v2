# Development Pipeline v2 维护规范

**状态：Accepted（2026-09-01 bootstrap）**

这份文档供维护者查阅规则：

- 职责与授权：第 2-3 节
- 文件、权限和版本证据：第 4-8 节
- agent 状态、容量和超时：第 9 节
- 设计、TDD 和候选轮次：第 10-12 节
- 评审与终态：第 13-14 节
- 安装与验收：第 15-16 节

真正交给 Codex 执行的指令位于五个运行时文件中，下文简称 `runtime`。本文件与 runtime 表达同一套合同，但这里优先可读性。

## 先记住四条原则

1. **主会话负责协调，不负责写代码。**
2. **只有 Implementer 可以写 candidate 或 tests；Verifier 只可写冻结的 scratch/output；评审不写文件。**
3. **没有证据就不继续；边界不清楚就停止。**
4. **同一候选最多修三轮，不能靠重置计数无限循环。**

## 1. 一次任务的全貌

只有用户显式调用 `$development-pipeline-v2` 时，流水线才会启动。

```text
启动前检查（Preflight）
   ↓
现状验证（BASELINE）：目标已经满足，还是确实需要改？
   ↓
失败测试或回归测试准备（RED / CHARACTERIZE）
   ↓
实现或修复（GREEN / FIX）
   ↓
完整验证（FULL）
   ↓
独立评审（Review）
   ↓
接受（ACCEPT），或带着完整问题进入下一轮修复
```

一次运行只处理一个明确任务和一个 Git 或 Non-Git 根目录。不会从另一个任务自动续跑，也不会留下长期状态文件。

## 2. 主会话与三个 agent 角色

| 角色 | 负责什么 | 明确不负责什么 |
| --- | --- | --- |
| 主会话（Coordinator） | 理解目标、冻结边界、调度 agent、核验证据、决定是否继续 | 不写 candidate、test 或 fix，不替 writer 应用 patch，也不重跑 test/build |
| `dp-v2-implementer` | 唯一逻辑 writer，按模式写测试或实现 | 不评审自己，不扩大 write set，不委派 |
| `dp-v2-verifier` | 运行 BASELINE、RED、FULL，收集独立证据 | 不修复，不修改 candidate、tests 或 inputs；只写冻结的 scratch/output |
| `dp-v2-reviewer` | 检查设计或候选，报告原始 findings | 不修复，不改变测试，不把个人偏好当问题 |

“唯一写入者”表示同一时刻最多只有一个 Implementer 修改文件。

测试准备和后续实现可以由不同 Implementer 依次完成，但写入时段不能重叠。

三个角色都不能继续委派子 agent。FULL 和 Review 每轮都使用 fresh agent，不能复用上一轮角色的结论。

## 3. 授权范围

用户调用一次后，同一目标和架构内的本地可逆工作可以完整走完：设计、测试、实现、验证、评审和修复都不需要逐轮确认。

只有这些情况需要重新询问：

- 目标或架构发生实质扩张
- 要接触生产环境或外部系统
- 涉及凭据、权限、破坏性操作或真实数据风险
- 要修改 Git history 或 index

普通的下一轮修复、重新运行验证、最终 SHA 都不属于重新授权点。

## 4. Preflight：动手前先把边界说清楚

主会话必须先读取：

- 当前目录适用的 `AGENTS.md`
- Git status 和最近提交
- 与任务相关的实现、测试入口、依赖和配置
- 用户已经存在但尚未提交的修改

接着按以下顺序找方案：

1. 仓库里是否已经有可复用实现
2. 已有依赖是否已经提供能力
3. 标准库或平台能力是否足够
4. 最后才新增最小实现

新增依赖、封装层、接口、配置项或抽象时，必须说明它解决的当前需求，以及代码中哪种已经存在的差异需要统一处理。

仅为减少代码行数、符合个人风格或应对不确定的未来需求，都不足以新增它。

在第一个 agent 派发前，必须冻结：

- 目标和验收条件
- 允许修改的文件与测试文件
- 只读输入
- 命令、工作目录、环境、执行顺序和依赖关系
- 临时输出及其清理责任人
- 禁止操作
- 用户已有 dirty paths
- 每个 lane 的 deadline 和轮询间隔
- 实际权限模式

任何一项无法枚举时，结果是 `BLOCKED`，不是先写再补手续。

## 5. 根目录和文件边界

Git 仓库从调用目录运行 `git rev-parse --show-toplevel`，再取 `realpath`。Non-Git 任务必须明确给出根目录。

所有 cwd、write paths、inputs、scratch 和 outputs 都必须在该根目录内。以下情况默认停止：

- 路径逃出根目录
- 不明确的 symlink
- 意外进入 nested repo 或 submodule
- 特殊文件无法可靠读取
- 实际 workspace 与声明根目录不一致

流水线保留用户已有修改，不会清理、吸收、覆盖或 reset 未授权变化。

## 6. 权限模式：不要把默认配置当成事实

Codex subagent 会继承父任务的实时权限设置。因此，agent TOML 中的 `sandbox_mode` 只是默认请求，不能单独证明实际隔离已经生效。

每个 payload 都要带上实际采用的 `effective_confinement`。

### HARD

只有在能证明以下事实时使用：

- Reviewer 实际是 read-only
- Implementer 和 Verifier 实际只有目标根目录的 workspace-write

此时才可以说边界由平台强制。

### AUDITED_FULL_ACCESS

只有同时满足这些条件时使用：

- 用户已在父任务明确选择 Full access
- 工作仍是本地、可逆的
- 当前检查不依赖硬隔离

此模式下必须：

- 继续遵守角色的逻辑写入边界
- 把 HOME、TMP、cache、bytecode 和命令输出定向到根目录内的预声明 scratch
- 记录根目录 tree manifest 和受保护文件哈希
- 禁止外部系统、凭据、生产操作和高风险 Git 操作
- 在报告中明确写出：边界不是 OS 强制，无法证明根目录外绝对零写入

如果某项检查必须依赖硬隔离，则返回 `BLOCKED(capability-unavailable)`。

## 7. Snapshot：为什么每一步都要确认“还是同一个版本”

测试结果只有在输入没有偷偷变化时才有意义。因此，主会话会为当前任务冻结 snapshot，并要求各角色在关键命令前后重放。

对于所有实际可写根目录，snapshot 至少记录：

- path
- 文件是否存在
- type 和 mode
- 普通文件内容哈希
- symlink target
- tracked、untracked 和 ignored 文件

如果无法观察完整可写范围，只能使用 disposable copy；不能把文字中的 allowlist 当成 Full access 的平台隔离。

Verifier 使用 workspace-write 时，前后 snapshot 只能证明“没有持久变化”，不能证明“从来没有瞬时写过”。

需要强零写保证的检查，必须真的使用 read-only candidate 加独立 scratch，或在 disposable copy 中运行。

每条验证命令要记录：

- 执行顺序
- argv、cwd 和 env
- 开始与结束 snapshot
- exit code 或 signal
- stdout/stderr 原文，或哈希加字节数
- 因依赖失败而跳过的项目
- 临时输出、清理和子进程退出情况

证据缺失、顺序不一致、命令范围错误、未声明输出或清理失败都会得到 `BLOCKED`。

## 8. Git 任务需要额外记录什么

从第一次 Git 读取开始，必须：

- 移除 `GIT_DIR`、`GIT_WORK_TREE`、`GIT_INDEX_FILE`
- 固定 `LC_ALL=C`
- 固定 `GIT_OPTIONAL_LOCKS=0`

Snapshot 必须原样保存这些 Git 事实。带 `-z` 的输出保留 NUL 分隔，binary diff 保留原始字节，不能先转成普通文本再比较：

- 根目录 realpath 和 `HEAD`
- `git status --porcelain=v1 -z --untracked-files=all`
- `git ls-files --stage -z`
- `git diff --binary --no-ext-diff --no-textconv --no-renames HEAD`
- `git ls-files --unmerged --stage -z`
- 声明路径的 `git --literal-pathspecs ls-files -v -z`

除命令输出外，每个声明路径还要记录是否存在、type、mode、内容哈希和 symlink target。

`-v` 只用于识别会改变工作树语义的 assume-unchanged 和 skip-worktree。fsmonitor-valid 是可变缓存位，不进入语义 snapshot，也不增加 `-f` 读取。

如果检测到 merge、cherry-pick、revert、rebase、sequencer 或 bisect，还要记录相关状态文件及目录后代的存在性、type、mode、内容哈希和 symlink target。

状态内容变化就是 drift；流水线不能自动恢复这些 Git 文件。除非任务本身就是处理该 Git 操作，否则停止。

所有实际可写根目录都要保留有序的执行前和执行后 manifest。Scratch 另行记录原始状态，并在结束时恢复到完全相同的状态。

## 9. Agent 生命周期

运行前要确认 Desktop 真的支持：

- 直接派发三个 custom roles
- 观察真实状态
- close 或 interrupt
- close 后再次 wait 得到 `not_found`
- release 后能继续 spawn

不能用 `create_thread`、`fork_thread` 或给 peer task 发消息来冒充 pipeline lane。

### payload_id

派发 agent 前，主会话先冻结完整 payload，再生成一个仅在本次运行中有效、从不重复且不承载业务含义的 `payload_id`。

主会话在 spawn 前必须确认：

- ID 存在，而且从未使用过
- 内存映射中的 payload、角色、模式、根目录和可写范围都与本次派发一致
- 只有上述检查通过，才允许 spawn，并把 handle 与预期 ID 绑定

检查失败时零派发并返回 `BLOCKED`。这张映射只存在于当前运行内，不序列化、不哈希、不持久化。

Agent 只负责收到一个非空、内部一致的 ID，并在最终结果里原样返回。

ID 缺失、多值或内部矛盾时，执行前 `BLOCKED`；缺 ID 的这类结果可以不回显 ID。

如果最终回显与 handle 预期 ID 不一致，主会话将它判为身份不一致的 `BLOCKED`，停止后续派发、检查 drift 并释放 handle。

这种情况不是 crash，也不能通过 replacement 重试。

### 合法首行

| 角色 | 合法首行 |
| --- | --- |
| Implementer | `PASS` 或 `BLOCKED` |
| Verifier | `PASS`、`FAIL_CANDIDATE` 或 `BLOCKED` |
| Reviewer | `PASS`、`VALID_FINDINGS` 或 `BLOCKED` |

没有 final、`errored`、过早 `not_found`、非法首行或互相矛盾的证据属于 crash。合法 `BLOCKED` 不会被替换。

Crash 只允许替换一次，而且前提是原 handle 已释放、没有未授权变化、没有残留。Writer 已产生 delta 或第二次 crash 时，直接 `BLOCKED`。

每个 agent 结束后，主会话都必须 close/release handle，并通过后续 wait/status=`not_found` 证明释放完成。之后才能派发依赖任务。

无法证明时返回 `BLOCKED(unreleased-agent)`。用户取消或整个运行进入 `BLOCKED` 时，要释放本次运行拥有的全部 handles。

### Capacity 和 deadline

容量不足不算 agent 崩溃，也不占候选轮次。

- 仍有 agent 未完全关闭：等其关闭并释放名额后重试
- 没有未关闭的 agent，或最后一个关闭后仍失败：`BLOCKED(capacity-unavailable)`

单次状态检查超时不算失败，只会安排下一次观察。只有任务总截止时间到期，主会话才停止新派发并 interrupt/close agent：

- 成功 release：`BLOCKED(deadline-exceeded)`
- 无法证明 release：`BLOCKED(unreleased-agent)`，优先级更高

独立只读评审可以按真实容量并行。Candidate writers 不能重叠；会写 scratch 的验证命令要串行。

## 10. 可选的 Design 门

只有高风险任务或存在多个实质方案时才启用 Design。

主会话为每份完整设计冻结：

- run-local `design_id`
- 稳定的 line 或 section anchors
- 当前 design cycle

所有 DESIGN Reviewer 必须使用同一个 ID 和 anchors。

内存中的设计问题用 `design_id:line` 或 `design_id:section` 定位；代码候选问题继续使用仓库 `path:line`。

最多允许三份完整设计。第三份仍有有效 P0-P3 时，终态是 `DESIGN_NOT_ACCEPTED`。

## 11. TDD 分支

### 11.1 BASELINE

修改前，fresh Verifier 对每个可执行 clear check 分类：

- `already-satisfied`：成功条件已经通过，且没有 skip/xfail
- `requires-change`：因目标尚未满足而失败

Wrong reason、弱检查、未执行检查或环境错误都不是 `requires-change`，而是 `BLOCKED`。

### 11.2 全部已经满足

如果所有项目都满足，而且没有新增长期测试的要求：

- `candidate_cycle=none`
- writer 数量为 0
- `changed_paths=[]`
- 直接执行 FULL 和 Review

两者都通过时直接 `ACCEPT`。只有 FULL 失败或出现有效 finding，才会建立修复批次；第一个真正形成候选的 writer 从 cycle 1 开始。

### 11.3 RED

需要新行为时，先复用已有的强失败测试；没有时由 Implementer 添加最小 test-only batch。

Fresh RED Verifier 必须确认整批测试：

- 被收集并执行
- 没有 skip/xfail
- 因冻结的目标原因失败
- 没有生产代码变化

最多允许三次完整 RED preparation。RED 本身不形成 candidate cycle。

### 11.4 CHARACTERIZE

行为已经正确、只是缺少长期回归测试时，不制造假的 production RED。

Characterization test 必须：

- 在真实 candidate 上 PASS
- 在冻结的 negative fixture 或 disposable counterfactual 上因目标原因 FAIL
- 不留下 candidate/input 持久变化
- 完整清理临时副本

没有安全、相关、可重放的反例时，结果是 `BLOCKED`。

如果 characterization 在 FULL 中被证明没有判别力，下一轮可以再次只修这些测试文件。生产代码保持不变，所有 RED targets 保留。

### 11.5 Mixed batch

同一任务可能既有真正缺失的行为，又有已经正确但缺回归测试的行为。

这时先顺序完成两类 test preparation：

```text
RED test preparation                 cycle_effect=NONE
CHARACTERIZE test preparation        cycle_effect=NONE
冻结全部 tests
GREEN / FIX production change        cycle_effect=FORM_CANDIDATE
```

两个 preparation writer 都不形成 candidate cycle。只有后面的 production delta 形成一个 cycle。

### 11.6 Writer phase 和 cycle_effect

| Mode | Phase | Cycle effect |
| --- | --- | --- |
| RED | `test-preparation` | `NONE` |
| mixed CHARACTERIZE | `test-preparation` | `NONE` |
| standalone CHARACTERIZE | `cycle-forming` | `FORM_CANDIDATE` |
| characterization repair | `cycle-forming` | `FORM_CANDIDATE` |
| GREEN / FIX | `cycle-forming` | `FORM_CANDIDATE` |

只有 `FORM_CANDIDATE` writer 满足以下全部条件时，主会话才在 FULL 前形成或递增 cycle 1、2、3：

- terminal PASS
- handle 已 release
- post snapshot 和 tree manifest 稳定
- delta 非空、完全可归因

Preparation、crash、`BLOCKED`、空 delta 或无法归因的 delta 都不递增。

## 12. FULL 和 candidate cycles

FULL 在一个稳定 snapshot 上重验：

- already-satisfied 回归义务
- frozen RED targets
- characterization 证据
- affected regression
- static、type、build
- 必要 runtime checks

依赖失败时可以跳过后继，但必须记录根失败和未执行命令。

Cycle 1 或 2 失败时，把 FULL failures 和有效 findings 合并为一个修复批次。

这个批次重新经过 BASELINE、必要的测试准备、一个 `FORM_CANDIDATE` writer、FULL 和全部 Review。

Cycle 3 仍失败或保留有效 finding 时：

- drain 并 release active handles
- 终止为 `CANDIDATE_NOT_ACCEPTED`
- 禁止下一次 `FORM_CANDIDATE` GREEN、FIX 或 CHARACTERIZE

RED 和 mixed preparation writers 不计入这个 guard。

## 13. Review 和 findings

Review 只在 FULL PASS 后开始。核心维度包括：

- correctness、scope、error/data flow
- TDD 和 regression
- repository consistency
- reuse、maintainability、anti-overdesign

Security、API、migration、performance、frontend、UX、accessibility 等维度按证据决定是否加入。不适用时要记录原因。

每个 finding 必须包含：

- ID
- P0、P1、P2 或 P3
- dimension
- 稳定 location
- 可重放 trigger/evidence
- impact
- constrained fix
- executable clear condition

没有现实正确性、安全、性能、维护、测试或操作影响的风格偏好和 LOC 收益，不是 finding。

Reviewer 返回的是 raw findings。主会话先完整保留它们，不能只留下摘要。

只有原因、影响、完整 constrained fix 和 clear condition 全部相同的项目才可以合并。同一个 ID 如果证据或影响不同，仍然要分别保留。

主会话随后逐项重放证据：

- 有可重放反证：标记为 `refuted`
- 其余项目：进入 effective finding set

Effective set 为空时，该 lane 为 effective PASS，不产生修复，也不增加 cycle。非空时，只有完整 effective set 可以进入修复批次。

Malformed result、malformed finding、lane `BLOCKED` 或未完成会立即使当前运行 `BLOCKED`，不能继续做 effective 复核。

## 14. 终态

一次运行只能有四类终态：

| 终态 | 含义 |
| --- | --- |
| `ACCEPT` | FULL 和全部有效 Review 通过，P0-P3 为零，输出和 handles 已清理 |
| `DESIGN_NOT_ACCEPTED` | 三份设计仍未收敛 |
| `CANDIDATE_NOT_ACCEPTED` | 三个 candidate cycles 仍未收敛 |
| `BLOCKED(reason)` | 权限、证据、边界、环境或生命周期条件不足 |

`ACCEPT` 报告根目录、目标范围、最终 snapshot、changed paths、验证与评审结果、已清除 findings、残余风险和未执行事项。

其他终态报告最后可信 snapshot、直接阻塞证据和 handle release 结果，不会自动续跑。

## 15. Runtime 交付边界

安装到 Codex 的 runtime 恰好五个文件：

```text
~/.codex/skills/development-pipeline-v2/SKILL.md
~/.codex/skills/development-pipeline-v2/agents/openai.yaml
~/.codex/agents/dp-v2-implementer.toml
~/.codex/agents/dp-v2-reviewer.toml
~/.codex/agents/dp-v2-verifier.toml
```

硬限制：

- 最多 220 个非空行
- 最多 24000 bytes
- `allow_implicit_invocation: false`
- Skill 目录不增加 `references/`、`scripts/` 或其他文件
- 不引用或安装 Ponytail
- 不修改受保护文件：
  - `~/.codex/skills/development-pipeline/SKILL.md`
  - `~/.codex/skills/development-pipeline/agents/openai.yaml`
  - `~/.codex/config.toml`
  - `~/.codex/AGENTS.md`

安装前后，四个受保护文件必须逐字节一致；v1 的 `allow_implicit_invocation` 必须继续为 `false`。

仓库里的 README、规范、安装器和 CI 是维护工具，不属于 runtime。

## 16. 安装和 bootstrap 验收

安装前必须：

1. 运行旧 runtime 的目标 RED，证明测试确实能区分 old/new。
2. 冻结五个目标文件和四个受保护文件的原始状态。记录每个目标文件原本存在还是缺失，并绑定内容 SHA。
3. 对现有目标创建权限为 `0600` 的备份。

安装后必须使用真实 direct agent 和 fresh session 证明：

- 新五文件已经 hot-load，并与安装 SHA 一致
- 三个 custom role 可以派发
- 每个 terminal 后能 release，并由后续 `not_found` 证明
- 四个受保护文件逐字节不变，v1 仍为 explicit-only

无法证明 hot-load 时，需要切换到可验证的新 Desktop 进程。

做不到就按安装前记录的文件内容或缺失状态恢复旧文件，并返回 `BLOCKED(reload-required)`。安装、验证或中断中的任何失败都必须执行同样的精确回滚。

Bootstrap 行为测试至少覆盖，而且必须检查真实平台事件、literal commands、manifest、delta、terminal 和 release，不能只扫描关键词：

- explicit-only
- main 零写入和唯一 writer
- all-satisfied、mixed、RED、CHARACTERIZE、FULL、Review
- cycle 1/2/3 和无第四个 cycle-forming writer
- deadline cancel 与 release
- capacity、wrong root、undeclared output、missing evidence、malformed final
- Git 和 Non-Git
- failed-install rollback
- 三个非空候选依次消耗 cycle 1、2、3，第三次失败后没有下一次 cycle-forming writer
- empty delta 和 crash 不增加 cycle
- Git staged/mode/binary、operation-state、assume-unchanged 和 skip-worktree drift

任何必需 case 无法真实诱发时，bootstrap 结果都是 `BLOCKED`，不能用静态检查降级通过。

所有临时 fixture、driver 和 scratch 最终必须不存在。

五个 runtime 文件满足预算、四个受保护文件逐字节不变、最终 Review 的 P0-P3 为零，才可以把规范状态标记为 `Accepted`。
