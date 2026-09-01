# Development Pipeline v2 最小运行规范

- 状态：`Accepted`（2026-09-01 bootstrap）；runtime 已安装并通过结构、Git/Non-Git 行为、deadline/release、P0-P3 清零与零残留验收。
- `必须`、`不得`、`BLOCKED` 是硬门禁；证据不足时 fail closed，不得以总结、关键词或口头确认替代。

## 1. 范围与授权

- 仅当前会话显式调用 `$development-pipeline-v2` 后运行；一次 run限一个 main、normalized Git/Non-Git root和冻结任务，不推断或跨线程续跑。
- 首次调用授权同一 scope/architecture内全部本地可逆 Design/TDD/FULL/Review/fix；仅实质扩张或生产、外部、凭据、权限、破坏性、数据、Git history/index风险再确认，其余缩界或 `BLOCKED`。
- run不留长期状态、不自改、不调用/修改v1、不自动续接；后续任务重新显式调用。

## 2. 角色与写入边界

- main是唯一 Coordinator，只读冻结、direct派发、等待、核验、汇总；不写 candidate/test/fix或代writer应用patch。三角色不委派，Design、BASELINE/RED/FULL Verify、Review用fresh agent。
- `dp-v2-implementer`是同时最多一个的逻辑writer；Verifier不改candidate/tests/inputs，Reviewer不写repo/candidate；两者仅按confinement使用预声明scratch/output。TOML `sandbox_mode`只是请求默认，不证明实际权限。
- Preflight读取并绑定parent及每个child的actual effective sandbox/permission profile；每个payload含 `effective_confinement=HARD|AUDITED_FULL_ACCESS`。HARD须证明Reviewer实际read-only、Implementer/Verifier为exact-root workspace-write，才可声称平台强制。
- AUDITED_FULL_ACCESS仅在用户已于parent turn显式选择Full access、任务本地可逆且无check要求hard confinement时允许。角色仍守逻辑边界，commands把HOME/TMP/cache/bytecode等定向到root内预声明scratch，冻结root/protected hashes和tree manifest，禁止外部/凭据/生产/Git危险，并报告“边界非OS强制、不能证明root外零写”；hard-required check即 `BLOCKED(capability-unavailable)`。
- Coordinator只重放只读snapshot/证据，不重跑test/build；角色不得把AUDITED描述为hard read-only或OS exact-root。

## 3. Preflight、复用与 root

- 先读适用 `AGENTS.md`、Git status/最近提交、实现、测试入口、依赖、配置和 dirty paths；Non-Git记录无Git证据。
- 依次检查 existing implementation/dependency、stdlib/platform，最后才最小新增；新依赖、wrapper、接口、配置或抽象须有当前需求和真实变化轴，LOC/风格不算理由。
- Git root从调用 cwd按第 4 节 env执行 `git rev-parse --show-toplevel`并取 `realpath`；Non-Git root须由任务明确给出并取 `realpath`，失败即 `BLOCKED`。
- cwd、write/input/scratch/output须在 root内；逃逸、嵌套repo、submodule、特殊文件、不明symlink或实际 writable root不符即 `BLOCKED`。
- 首个dispatch前冻结 scope/architecture/batch、write/test/input/output边界、commands/env、cleanup/prohibited/dirty paths及effective confinement；每个lane dispatch前冻结有限deadline/poll，同授权内不再询问，无法枚举即 `BLOCKED`。
- 保留用户改动，不清理、吸收、覆盖或重置未授权变化；默认不做Git history/index mutation。

## 4. Snapshot 与证据

- 首个 Git read 起移除 `GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE`，固定 `LC_ALL=C`、`GIT_OPTIONAL_LOCKS=0`；无法排除 poisoned env 或 `HEAD` 不存在即 `BLOCKED`。Coordinator 冻结 literal read-only snapshot profile、commands/env和普通 SHA-256，不造 encoder。
- Git profile保存 root realpath、`HEAD`、raw NUL `status --porcelain=v1 -z --untracked-files=all`、`ls-files --stage -z`、raw binary `diff --binary --no-ext-diff --no-textconv --no-renames HEAD`、`ls-files --unmerged --stage -z`、声明路径 `--literal-pathspecs ls-files -v -z`及其 absence/type/mode/hash/symlink。scoped `-v`只解析影响工作树语义的 assume-unchanged/skip-worktree；fsmonitor-valid仅是可变缓存位，不入semantic snapshot/fixture且不加 `-f`。
- 对检测到的 merge/cherry-pick/revert/rebase/sequencer/bisect state路径及目录后代记录 absence/type/mode/content hash/symlink；内容变化即 drift，不自动恢复Git文件，未授权解决该操作即 `BLOCKED`。Skill与三role检查同一profile完整性；允许per-repo literal command/普通SHA，不造新Git协议。
- 每个actual writable root执行前后生成有序tree manifest，覆盖tracked/untracked/ignored的path/type/mode/hash/symlink；AUDITED另复核protected hashes。全树观察不可行时只能用disposable copy，否则 `BLOCKED`；不得把allowlist声称为Full access平台限制。scratch独立冻结preimage/restore。
- Verifier 使用 `workspace-write` 时，前后 manifest 只证明无持久 delta，不证明无瞬时写；需要强零写保证的 check 必须实际 hard read-only+scratch 或 disposable copy，否则该 check `BLOCKED`。daemon/delayed child 必须有退出、teardown和最终 manifest证据。
- Verifier 每条 command 记录 ordinal、argv、cwd/env、start/end snapshot、exit/signal、stdout/stderr raw或 SHA+byte count、dependency skip、outputs/cleanup；缺失、错序、stale或 wrong-scope evidence 均 `BLOCKED`。未归因 drift、越界、undeclared output、非法 test mutation或 restore失败不得清理后继续。

## 5. Desktop worker 生命周期与并发

- Capability gate 只允许 main 实际 direct custom-role spawn/wait/status/close-or-interrupt；禁止 `create_thread`、`fork_thread` 或向 peer task 发消息冒充 lane。run 前须证明三 role可派发、真实 status、close 后 wait=`not_found`、release 后可再次 spawn；缺 direct 能力即 `BLOCKED(capability-unavailable)`，不得自造 token/handle。
- Coordinator在spawn前冻结payload、分配run内never-used opaque payload_id，核验present/unused及map entry与payload/role/mode/root/write_set一致；通过才spawn并绑定handle+expected ID，失败零dispatch、`BLOCKED`，不hash/持久化。role只检查单一非空、内部一致并原样回显，不知map/reuse；missing/multi/conflict可预先BLOCKED，missing-ID final可无echo。echo不等expected是terminal identity `BLOCKED`，非crash且不replacement；停派、查drift、release，匹配后再查status/evidence。
- final首行仅允许 Implementer `PASS|BLOCKED`、Verifier `PASS|FAIL_CANDIDATE|BLOCKED`、Reviewer `PASS|VALID_FINDINGS|BLOCKED`；正文满足第 4/8 节证据，Reviewer含 findings或空集。
- 除上条ID规则外，无final、`errored`、final前 `not_found`、非法首行或缺/矛盾证据均为crash；合法 `BLOCKED`不重派，malformed finding使run `BLOCKED`。
- terminal后真实 close/release，后续 wait/status=`not_found`可作证明；否则停派并 `BLOCKED(unreleased-agent)`。crash仅在已 release、零未归因 delta/residue时重派一次；writer有 delta或二次 crash即 `BLOCKED`。
- spawn capacity error 不算 crash或 cycle：若仍有 run-owned active handle，work保持 pending且只在真实 release事件后重试；零 run-owned active时首次失败，或最后一个 release后重试仍失败，立即 `BLOCKED(capacity-unavailable)`。不得忙循环、预设容量或 close/interrupt外部 handle。
- poll timeout只触发下次观察；`execution_deadline`到期是预授权cancel事件，不伪装为agent结果：停派，interrupt/close该handle；release成功为 `BLOCKED(deadline-exceeded)`，否则 `BLOCKED(unreleased-agent)`优先。用户取消/run-level `BLOCKED`同样停派并释放run-owned handles。
- 独立只读 lanes尽量并行，candidate writer不并行；写 scratch/output 的 verifier commands串行，纯只读 commands可并行。scratch须预声明、独占、owner清理并恢复 preimage。

## 6. 可选 Design 门

- 仅高风险/多方案启用Design。Coordinator冻结每份design时分配稳定run-local design_id与line/section anchors，绑定cycle并随全部DESIGN payload提供；不持久化/hash。fresh lanes检查scope/architecture、数据/错误、验证、复用、风险。
- Coordinator按第8节复核raw `VALID_FINDINGS`；全证伪即PASS且无下一份，仅完整effective P0-P3可合成下一design。
- 最多三份design且每份重审全部维度；第三份effective finding即 `DESIGN_NOT_ACCEPTED`，全部effective PASS才接受design；实质architecture扩张仍按第1节确认。

## 7. 批量 TDD 与 Candidate Flow

- 每轮冻结完整batch、clear checks、预期原因、test/write paths、commands/order/dependencies；fresh BASELINE Verifier同snapshot逐项分为 `already-satisfied`或target-caused `requires-change`，wrong reason、weak/未执行或环境错误即 `BLOCKED`。
- all-satisfied且无持久test请求时，冻结target snapshot为 `candidate_cycle=none` review target，`writer_count=0`、`changed_paths=[]`，完整FULL+effective Review PASS直接ACCEPT。只有FULL `FAIL_CANDIDATE`或effective finding非空才建repair；首个合法cycle-forming writer形成cycle1。
- Implementer payload含 `phase=test-preparation|cycle-forming`、`cycle_effect=NONE|FORM_CANDIDATE`；仅允许RED=test-preparation/NONE、mixed CHARACTERIZE=test-preparation/NONE、standalone/repair CHARACTERIZE及GREEN/FIX=cycle-forming/FORM_CANDIDATE。one writer仅指同时最多一个。
- mixed先顺序完成全部requires-change RED与already-satisfied持久覆盖CHARACTERIZE test preparation，均NONE；冻结全部tests后，仅GREEN/FIX production delta形成一个cycle。RED可复用strong target failure，否则添加最小test-only batch；整批须执行、无skip/xfail并按冻结原因FAIL，最多三次preparation。
- CHARACTERIZE只覆盖已满足行为：真实candidate上test PASS，冻结negative fixture/disposable counterfactual上因目标原因FAIL，且无持久candidate/input delta并清理副本；无安全、相关、可重放counterfactual即 `BLOCKED`。其FULL失败后的repair可再次CHARACTERIZE，仅改该test paths、production不变并preserve全部RED targets。
- RED PASS后冻结tests/targets/commands/evidence；GREEN/FIX只改production且不弱化tests。所有writer遵守phase/effect组合，delta须非空、稳定、完全可归因。
- 仅FORM_CANDIDATE writer terminal+release且post snapshot/tree manifest稳定后，Coordinator在FULL前原子形成/递增cycle1/2/3；NONE、crash、`BLOCKED`、empty/unattributable delta不递增。FULL failure/effective finding已消耗该cycle。
- FULL重验regression obligations、RED targets、characterization、affected regression/static/type/build/runtime，并要求稳定snapshot、无持久candidate/input delta、outputs恢复和daemon退出；通过后运行全部Review lanes。
- no-cycle/cycle1/2合法failure batch重走BASELINE、preparation、一个FORM_CANDIDATE writer、FULL、全Review。cycle3失败后drain并 `CANDIDATE_NOT_ACCEPTED`，禁止下一次FORM_CANDIDATE GREEN/FIX/CHARACTERIZE；preparation writers不属candidate guard。

## 8. Review 与 finding 契约

- 每轮Review对同一target snapshot/changed paths/FULL evidence用fresh read-only lanes；core覆盖correctness/scope/error/data flow、TDD/regression、repo consistency、reuse/maintainability/anti-overdesign。
- 按冻结证据增加适用 security、API、migration、performance、frontend、UX、accessibility lanes；不适用须留理由，专项输出仍受同一 snapshot/finding/复核门禁。
- 每个finding含ID、P0-P3、dimension、trigger/evidence、impact、constrained fix、clear condition；CANDIDATE location须repo `path:line`，DESIGN须原样使用payload的 `design_id:line|design_id:section` anchor。无现实影响的偏好/LOC不是finding。
- raw `VALID_FINDINGS` 先保留全部项目；只合并实质原因、影响、修复和 clear condition相同项，同 ID但证据或影响不同仍保留。malformed result/finding、lane `BLOCKED`或未完成直接使 run `BLOCKED`，不得进入复核。
- Coordinator 对每个结构合法 raw finding独立重放 trigger/evidence和 clear condition，只能以可重放反证标记 `refuted`；其余有效 P0-P3组成 effective finding set，Reviewer不写 fix。
- effective set为空时该 lane/轮次为 effective PASS，不产生 repair、不增加 candidate/design cycle；非空时只有该完整 set进入下一轮。`ACCEPT`依据全部 lanes的 effective outcome，不能依据未经复核的 raw结论或总结。

## 9. 终态与交付报告

- run 终态仅为 `ACCEPT`、`DESIGN_NOT_ACCEPTED`、`CANDIDATE_NOT_ACCEPTED` 或 `BLOCKED(reason)`；前三者不得掩盖任何优先发生的 run-level `BLOCKED`。
- `ACCEPT` 报告 root/scope、最终 snapshot、changed paths、FULL/Review证据、已清零 findings、残余风险和未执行项；其他终态报告最后可信 snapshot、阻塞与 release证据且不自动继续。不得声称未完成的发布、提交或外部交付。

## 10. Runtime 交付边界

- runtime 恰好五个文件：`~/.codex/skills/development-pipeline-v2/SKILL.md`、`~/.codex/skills/development-pipeline-v2/agents/openai.yaml`、`~/.codex/agents/dp-v2-implementer.toml`、`~/.codex/agents/dp-v2-reviewer.toml`、`~/.codex/agents/dp-v2-verifier.toml`。
- 五文件合计不超过 220 个 NF 非空行和 24000 bytes；`openai.yaml` 必须设置 `allow_implicit_invocation: false`。不得创建 `references/`、`scripts/`、hooks、state/manifest 文件或第六交付物，不引用或安装 Ponytail。
- runtime 不修改上述五文件。protected inputs 还包括 v1 的 `~/.codex/skills/development-pipeline/SKILL.md`、`~/.codex/skills/development-pipeline/agents/openai.yaml`、`~/.codex/config.toml` 和 `~/.codex/AGENTS.md`；安装前后逐字节一致，v1保持 explicit-only。
- 外部验收可在临时 root创建非交付 fixture/driver，由唯一 owner清理并证明零 residue；`quick_validate.py` 仅证明 Skill结构，不替代行为验收。

## 11. Bootstrap 行为验收

- bootstrap支持时优先隔离 `CODEX_HOME`，但不强制；否则仅当前外部 bootstrap owner可执行 live maintenance，且先证明无其他 active v2 run。每 case冻结 driver/prompt/model/env/input并用真实 direct agent、临时 Git/Non-Git fixture。
- 写目标前先跑旧 runtime目标 RED且须因目标缺失失败；冻结五目标 exact preimage/absence与 protected inputs，为现存目标建 `0600`备份。唯一 writer只安装五文件，额外目标或 protected drift均失败。
- 安装后用 fresh direct agent/session证明 hot-load并绑定五文件 SHA。无法证明 hot-load时，只有 external owner可切换到不同 Desktop process generation后继续；没有可验证 reload能力则恢复旧 preimage/absence并 `BLOCKED(reload-required)`。
- 任一失败/中断都恢复 exact preimage/absence，必要时 reload旧版本，再复核 protected inputs与零 residue；成功才保留 new。该 rollback仅属外部安装事务，不是 runtime对 `BLOCKED` 的恢复机制。
- fixtures保留 explicit-only、main零写、唯一writer、all-satisfied/mixed、raw findings全证伪、完整TDD/FULL/Review、并发/scratch、Git/Non-Git、release后spawn、live hot-load，以及原 wrong root/escape、undeclared output、缺RED/Verify证据、malformed final、writer crash、P0-P3、capacity/handle和rollback负测。
- 新增：三个nonempty delta各自FULL失败须形成cycle1/2/3且无第四dispatch，empty/crash不递增；never-final须deadline cancel并release；missing-regression须candidate PASS、counterfactual FAIL、test-only cycle后Review清零。
- Git/evidence fixtures加入 poisoned env、staged/mode/binary drift、operation-state content-only drift、random ignored output、stale/wrong-scope、write-restore/daemon/scratch冲突；fsmonitor-valid单独变化不阻塞，assume-unchanged/skip-worktree变化必须检出。
- driver核验平台事件、literal commands、manifest/delta、terminal/release和文件事实，regex仅辅助；无法真实诱发必需 case即 `BLOCKED`。清理后须证明临时 root零 residue、五文件预算合规、protected inputs逐字节不变。

## 12. 最终接受条件

- 仅当最终 snapshot在 FULL/Review起止稳定、FULL与所有 effective lanes PASS、P0-P3为零、handles已 release、outputs已恢复、交付边界与 bootstrap cases通过时 `ACCEPT`；缺失/不可重放证据、drift、undeclared output或双三轮未收敛均不接受。
