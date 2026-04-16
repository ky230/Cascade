> [!CAUTION]
> **CANCELLED** — Git 命令已全部砍掉。用户自然语言 + BashTool 即可完成。保留此文件作为 Claude Code 源码参考。

# Phase 9.5: Batch 5 — Git 工作流命令 (5 commands)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 实现 `/commit`, `/commit-push-pr`, `/pr-comments`, `/review`, `/security-review` 五个 Git 工作流命令。

**架构:** `BaseCommand` + `CommandContext`，新建 `commands/git/` 子包。

**前置条件:** Phase 9.4.5 (Batch 4.5) 完成。

---

## 📊 命令总览

| 命令 | Claude Code 参考源码 | Cascade 实现级别 | 架构限制 |
|------|---------------------|-----------------|---------|
| `/commit` | `src/commands/commit.ts` (93行, `type: 'prompt'`) | ⚠️ 简化版 | 无 `type: 'prompt'` 命令模式 |
| `/commit-push-pr` | `src/commands/commit-push-pr.ts` (159行, `type: 'prompt'`) | ⚠️ 简化版 | 无 `type: 'prompt'` + 依赖 `gh` CLI |
| `/pr-comments` | `src/commands/pr_comments/index.ts` (51行, `createMovedToPluginCommand`) | ⚠️ 简化版 | 已被 CC 迁移到 plugin 系统 |
| `/review` | `src/commands/review.ts` (58行, `type: 'prompt'`) | ⚠️ 简化版 | 无 `type: 'prompt'`；CC 还有 `/ultrareview` |
| `/security-review` | `src/commands/security-review.ts` (244行, `createMovedToPluginCommand`) | ⚠️ 简化版 | 已被 CC 迁移到 plugin；244 行安全审查 prompt |

> [!IMPORTANT]
> **这 5 个 Git 命令全部是 `type: 'prompt'` — Claude Code 最复杂的命令类型。**
> prompt 型命令的工作方式是：将一段精心构造的 prompt 注入到 LLM 对话中，让 LLM 执行 git 操作。
> Cascade 没有 `type: 'prompt'` 命令基础设施，所以这些命令改为 **subprocess 直接执行 git** + 文本输出。
> 复杂的 LLM 驱动版本将在 Phase 10+ 中随 prompt 命令系统一起实现。

---

## Claude Code 源码参考详情

### `/commit` 参考分析

**源码:** [commit.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/commit.ts) — 93行
- `type: 'prompt'`，`name: 'commit'`
- `ALLOWED_TOOLS: ['Bash(git add:*)', 'Bash(git status:*)', 'Bash(git commit:*)']`
- `getPromptContent()` 注入 prompt 包含：
  - `!git status`, `!git diff HEAD`, `!git branch --show-current`, `!git log --oneline -10`（`!` 语法是 executeShellCommandsInPrompt 的宏展开）
  - Git Safety Protocol（8 条规则）
  - 提交消息格式：`git commit -m "$(cat <<'EOF' ... EOF)"`（heredoc 语法）
  - `commitAttribution` —— Anthropic 归因文本
- `executeShellCommandsInPrompt()` — 将 `!command` 宏替换为实际输出

**Cascade 适配:** 不通过 LLM 生成 commit message。直接运行 `git add -A && git commit`，让用户提供 message（通过 args），或用基础模板。

### `/commit-push-pr` 参考分析

**源码:** [commit-push-pr.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/commit-push-pr.ts) — 159行
- `type: 'prompt'`，`name: 'commit-push-pr'`
- `ALLOWED_TOOLS` 包含 git checkout, add, status, push, commit, 以及 `gh pr create/edit/view/merge`
- 完整 PR 工作流 prompt：
  1. 创建新分支（如果在 main 上）— 分支名用 `SAFEUSER/feature-name`
  2. 单个 commit + heredoc 格式的 commit message + attribution
  3. Push 到 origin
  4. 检测是否已有 PR → `gh pr edit` 或 `gh pr create`
  5. 可选：公司内部 Slack 通知
- `getDefaultBranch()`, `getEnhancedPRAttribution()` — 运行时获取

**Cascade 适配:** 分步执行 git 命令（不通过 LLM）。需要 `gh` CLI。

### `/pr-comments` 参考分析

**源码:** [pr_comments/index.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/pr_comments/index.ts) — 51行
- 使用 `createMovedToPluginCommand()`——**这个命令已经被迁移到 plugin 系统**
- 保留 `getPromptWhileMarketplaceIsPrivate()` 作为后备
- 后备 prompt 使用 `gh api` 获取 PR comments 和 review comments
- 格式化输出：`@author file.ts#line` + diff_hunk + quoted comment

**Cascade 适配:** 直接调用 `gh pr view --comments` 和 `gh api`。

### `/review` 参考分析

**源码:** [review.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/review.ts) — 58行
- `type: 'prompt'`，`name: 'review'`
- `LOCAL_REVIEW_PROMPT` — 简洁的代码审查 prompt（使用 `gh pr view/diff`）
- 同文件还导出 `ultrareview`（远程 bug hunter，`type: 'local-jsx'`，付费增强审查）

**Cascade 适配:** 直接运行 `gh pr diff` + 文本输出，不通过 LLM 审查。

### `/security-review` 参考分析

**源码:** [security-review.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/security-review.ts) — 244行
- `createMovedToPluginCommand()`——已迁移到 plugin
- 188 行的安全审查 prompt，包含：
  - 安全类别（Input Validation, Auth, Crypto, Injection, Data Exposure）
  - 3 阶段分析方法论（Repository Context → Comparative → Vulnerability Assessment）
  - 严格的 False Positive 过滤规则（17 条排除规则 + 12 条 Precedents）
  - 置信度评分体系（0.7 以下不报告）
  - 要求使用 sub-task 并行分析 + 过滤

**Cascade 适配:** 直接运行 `git diff` 显示变更，安全审查文字提示用户手动审查。LLM 驱动的安全审查需要 prompt 命令系统。

---

## 实施步骤

### Task 1: 创建 git 命令子包

**文件:**
- 创建: `src/cascade/commands/git/__init__.py`
- 创建: `src/cascade/commands/git/commit.py`
- 创建: `src/cascade/commands/git/commit_push_pr.py`
- 创建: `src/cascade/commands/git/pr_comments.py`
- 创建: `src/cascade/commands/git/review.py`
- 创建: `src/cascade/commands/git/security_review.py`

#### `/commit`

```python
# src/cascade/commands/git/commit.py
from cascade.commands.base import BaseCommand, CommandContext
import subprocess


class CommitCommand(BaseCommand):
    """Create a git commit.

    Reference: claude-code src/commands/commit.ts (93 lines)
    Claude Code impl: type='prompt'. Injects prompt with git status/diff/log
    context via executeShellCommandsInPrompt(). LLM generates commit message
    following repo's commit style. ALLOWED_TOOLS: git add/status/commit only.
    Includes Git Safety Protocol (8 rules) and heredoc commit syntax.
    commitAttribution appended for Anthropic attribution.
    Cascade impl: simplified subprocess — runs git add + git commit.
    User provides commit message via args, or prompted interactively.
    No LLM-generated commit messages (requires prompt command system).
    """
    name = "commit"
    description = "Create a git commit"
    category = "Git"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        msg = args.strip()
        if not msg:
            await ctx.output_rich(
                "[dim]Usage: /commit <message>\n"
                "Example: /commit fix ttH signal region binning[/dim]"
            )
            return

        # Check for changes
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=10
        )
        if not status.stdout.strip():
            await ctx.output_rich("[dim]No changes to commit.[/dim]")
            return

        # Stage all and commit
        subprocess.run(["git", "add", "-A"], timeout=10)
        result = subprocess.run(
            ["git", "commit", "-m", msg],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            await ctx.output_rich(
                f"[#00d7af]Committed:[/#00d7af] {msg}\n"
                f"[dim]{result.stdout.strip()}[/dim]"
            )
        else:
            await ctx.output_rich(
                f"[red]Commit failed:[/red]\n[dim]{result.stderr.strip()}[/dim]"
            )
```

#### `/commit-push-pr`

```python
# src/cascade/commands/git/commit_push_pr.py
from cascade.commands.base import BaseCommand, CommandContext
import subprocess
import shutil


class CommitPushPrCommand(BaseCommand):
    """Commit, push, and open a PR.

    Reference: claude-code src/commands/commit-push-pr.ts (159 lines)
    Claude Code impl: type='prompt'. Most complex prompt command. Injects
    full PR workflow prompt: create branch if on main (SAFEUSER prefix),
    single commit with heredoc + attribution, push to origin, gh pr create
    or gh pr edit (detects existing PR). Supports Slack notification.
    ALLOWED_TOOLS: git checkout/add/status/push/commit + gh pr create/edit
    /view/merge + ToolSearch + Slack tools.
    Cascade impl: simplified subprocess chain — requires user to provide
    commit message. Runs git add, commit, push, gh pr create sequentially.
    No LLM-driven branch naming or commit message generation.
    """
    name = "commit-push-pr"
    description = "Commit, push, and open a PR"
    aliases = ["/pr"]
    category = "Git"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        if not shutil.which("gh"):
            await ctx.output_rich(
                "[red]GitHub CLI (gh) not found. "
                "Install: https://cli.github.com[/red]"
            )
            return

        msg = args.strip()
        if not msg:
            await ctx.output_rich(
                "[dim]Usage: /commit-push-pr <commit message>\n"
                "  or:  /pr <commit message>[/dim]"
            )
            return

        steps = [
            ("git add -A", ["git", "add", "-A"]),
            (f"git commit", ["git", "commit", "-m", msg]),
            ("git push", ["git", "push", "--set-upstream", "origin", "HEAD"]),
        ]

        for label, cmd in steps:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                # git commit may fail if nothing to commit — not fatal
                if "nothing to commit" in result.stdout + result.stderr:
                    continue
                await ctx.output_rich(
                    f"[red]{label} failed:[/red]\n"
                    f"[dim]{result.stderr.strip()}[/dim]"
                )
                return

        # Create PR
        pr_result = subprocess.run(
            ["gh", "pr", "create", "--fill"],
            capture_output=True, text=True, timeout=30
        )
        if pr_result.returncode == 0:
            pr_url = pr_result.stdout.strip()
            await ctx.output_rich(
                f"[#00d7af]PR created:[/#00d7af] {pr_url}"
            )
        else:
            # Maybe PR already exists
            if "already exists" in pr_result.stderr:
                await ctx.output_rich(
                    "[dim]PR already exists. Pushed changes.[/dim]"
                )
            else:
                await ctx.output_rich(
                    f"[yellow]Pushed, but PR creation failed:[/yellow]\n"
                    f"[dim]{pr_result.stderr.strip()}[/dim]"
                )
```

#### `/pr-comments`

```python
# src/cascade/commands/git/pr_comments.py
from cascade.commands.base import BaseCommand, CommandContext
import subprocess
import shutil


class PrCommentsCommand(BaseCommand):
    """Get comments from a GitHub pull request.

    Reference: claude-code src/commands/pr_comments/index.ts (51 lines)
    Claude Code impl: createMovedToPluginCommand() — migrated to plugin.
    Fallback prompt uses gh api to fetch PR-level and review comments,
    formats as @author file.ts#line with diff_hunk context.
    Cascade impl: simplified — runs gh pr view --comments directly.
    """
    name = "pr-comments"
    description = "Get comments from a GitHub PR"
    category = "Git"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        if not shutil.which("gh"):
            await ctx.output_rich(
                "[red]GitHub CLI (gh) not found.[/red]"
            )
            return

        pr_num = args.strip()
        if pr_num:
            cmd = ["gh", "pr", "view", pr_num, "--comments"]
        else:
            cmd = ["gh", "pr", "view", "--comments"]

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            if output:
                await ctx.output_rich(f"[bold]PR Comments[/bold]\n\n{output}")
            else:
                await ctx.output_rich("[dim]No comments found.[/dim]")
        else:
            await ctx.output_rich(
                f"[red]Failed:[/red] {result.stderr.strip()}"
            )
```

#### `/review`

```python
# src/cascade/commands/git/review.py
from cascade.commands.base import BaseCommand, CommandContext
import subprocess
import shutil


class ReviewCommand(BaseCommand):
    """Review a pull request.

    Reference: claude-code src/commands/review.ts (58 lines)
    Claude Code impl: type='prompt'. LOCAL_REVIEW_PROMPT instructs LLM to:
    1. gh pr list (if no PR number)
    2. gh pr view <number> (PR details)
    3. gh pr diff <number> (diff)
    4. Analyze and provide thorough review (quality, style, perf, tests, security)
    Also exports /ultrareview (remote bug hunter, paid CCR feature).
    Cascade impl: simplified — shows PR diff for manual review.
    No LLM-driven code review (requires prompt command system).
    """
    name = "review"
    description = "Review a pull request"
    category = "Git"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        if not shutil.which("gh"):
            await ctx.output_rich(
                "[red]GitHub CLI (gh) not found.[/red]"
            )
            return

        pr_num = args.strip()
        if not pr_num:
            # List open PRs
            result = subprocess.run(
                ["gh", "pr", "list"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                await ctx.output_rich(
                    f"[bold]Open PRs[/bold]\n\n{result.stdout.strip()}\n\n"
                    f"[dim]Usage: /review <PR number>[/dim]"
                )
            else:
                await ctx.output_rich(
                    f"[red]Failed:[/red] {result.stderr.strip()}"
                )
            return

        # Show PR details + diff
        view = subprocess.run(
            ["gh", "pr", "view", pr_num],
            capture_output=True, text=True, timeout=15
        )
        diff = subprocess.run(
            ["gh", "pr", "diff", pr_num],
            capture_output=True, text=True, timeout=30
        )
        if view.returncode == 0:
            await ctx.output_rich(
                f"[bold]PR #{pr_num}[/bold]\n\n{view.stdout.strip()}"
            )
        if diff.returncode == 0:
            colorized = self._colorize_diff(diff.stdout.strip())
            await ctx.output_rich(f"\n[bold]Diff[/bold]\n\n{colorized}")

    def _colorize_diff(self, diff: str) -> str:
        lines = []
        for line in diff.split("\n")[:200]:  # Cap at 200 lines
            if line.startswith("+"):
                lines.append(f"[green]{line}[/green]")
            elif line.startswith("-"):
                lines.append(f"[red]{line}[/red]")
            elif line.startswith("@@"):
                lines.append(f"[cyan]{line}[/cyan]")
            else:
                lines.append(line)
        return "\n".join(lines)
```

#### `/security-review`

```python
# src/cascade/commands/git/security_review.py
from cascade.commands.base import BaseCommand, CommandContext
import subprocess


class SecurityReviewCommand(BaseCommand):
    """Security review of pending changes.

    Reference: claude-code src/commands/security-review.ts (244 lines)
    Claude Code impl: createMovedToPluginCommand() — migrated to plugin.
    Contains 188-line security review prompt with:
    - 6 security categories (Input Validation, Auth, Crypto, Injection,
      Code Execution, Data Exposure)
    - 3-phase analysis (Repository Context → Comparative → Vulnerability)
    - 17 hard exclusion rules + 12 precedents for false positive filtering
    - Confidence scoring (>0.8 to report)
    - Sub-task parallelization for vulnerability analysis
    Cascade impl: simplified — shows git diff for manual security review.
    Full LLM-driven security analysis requires prompt command system.
    """
    name = "security-review"
    description = "Security review of pending changes"
    category = "Git"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        result = subprocess.run(
            ["git", "diff", "origin/HEAD..."],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode != 0:
            # Fallback to HEAD diff
            result = subprocess.run(
                ["git", "diff", "HEAD"],
                capture_output=True, text=True, timeout=30
            )

        if result.returncode != 0:
            await ctx.output_rich(
                f"[red]git diff failed:[/red] {result.stderr.strip()}"
            )
            return

        diff = result.stdout.strip()
        if not diff:
            await ctx.output_rich("[dim]No changes to review.[/dim]")
            return

        # Show diff with security-focused header
        lines_count = diff.count("\n") + 1
        files_changed = len([
            l for l in diff.split("\n") if l.startswith("diff --git")
        ])

        await ctx.output_rich(
            f"[bold yellow]Security Review[/bold yellow]\n"
            f"  Files changed: {files_changed}\n"
            f"  Diff lines: {lines_count}\n\n"
            f"[dim]Review the diff below for:[/dim]\n"
            f"  • Hardcoded secrets/API keys\n"
            f"  • Command/SQL injection\n"
            f"  • Path traversal\n"
            f"  • Auth bypass\n"
            f"  • Unsafe deserialization\n\n"
            f"[dim](LLM-driven security analysis coming in a future release)[/dim]"
        )
```

### Task 2: 注册到 CascadeApp

**文件:** 修改 `src/cascade/ui/textual_app.py`

```python
        from cascade.commands.git.commit import CommitCommand
        from cascade.commands.git.commit_push_pr import CommitPushPrCommand
        from cascade.commands.git.pr_comments import PrCommentsCommand
        from cascade.commands.git.review import ReviewCommand
        from cascade.commands.git.security_review import SecurityReviewCommand
        self.router.register(CommitCommand())
        self.router.register(CommitPushPrCommand())
        self.router.register(PrCommentsCommand())
        self.router.register(ReviewCommand())
        self.router.register(SecurityReviewCommand())
```

### Task 3: 验证 + 手动测试

```bash
cascade
# /commit fix signal region        → git add -A && git commit -m "fix signal region"
# /pr fix signal region            → commit + push + gh pr create
# /pr-comments                     → 当前 PR 评论
# /review                          → 列出 open PRs
# /review 42                       → 显示 PR #42 详情 + diff
# /security-review                 → 显示 diff + 安全审查提示
# /help                            → Git 分组含 5 个命令
```

---

## L1~L4 验收标准

| Level | 检查项 | 标准 |
|-------|--------|------|
| L1 | `commands/git/` 含 6 个 .py 文件 | `ls` 确认 |
| L2 | 每个命令 docstring 标注 Claude Code 参考路径 + `type: 'prompt'` 说明 | `grep -r "Reference:" src/cascade/commands/git/` |
| L3 | `/commit fix test` 成功创建 commit；`/review` 列出 open PRs | 手动验证（需要 git repo） |
| L4 | `/pr` 别名触发 `/commit-push-pr`；`gh` 不存在时显示安装链接 | 手动测试 |

---

## 与 Claude Code 的差异汇总

| 命令 | Claude Code | Cascade | 差异原因 |
|------|-------------|---------|---------|
| `/commit` | 93 行 prompt → LLM 生成 commit message | subprocess `git commit -m <user_msg>` | 无 prompt 命令系统 |
| `/commit-push-pr` | 159 行 prompt → 完整 PR 工作流（分支+commit+push+PR+Slack） | subprocess 链式执行 | 无 prompt 系统 + 无 Slack |
| `/pr-comments` | `createMovedToPluginCommand` → plugin 系统 | `gh pr view --comments` | 无 plugin 系统 |
| `/review` | prompt → LLM 代码审查 + `/ultrareview` 付费远程审查 | `gh pr diff` 输出 | 无 prompt + 无 ultrareview |
| `/security-review` | 244 行安全审查 prompt（17 排除规则 + 置信度评分 + 并行 sub-task） | diff + 安全检查清单提示 | 无 prompt 系统 |
