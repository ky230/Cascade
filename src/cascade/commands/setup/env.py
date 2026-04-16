from cascade.commands.base import BaseCommand, CommandContext
import os


class EnvCommand(BaseCommand):
    """Show environment variables relevant to Cascade.

    Reference: claude-code src/commands/env/index.js (2 lines)
    Claude Code impl: DISABLED stub — isEnabled: () => false, isHidden: true.
    The command exists in the codebase but is never shown to users.
    Cascade impl: ORIGINAL implementation showing CASCADE_* env vars
    and HEP-specific variables (SCRAM_ARCH, CMSSW_BASE, X509_USER_PROXY).
    This is a Cascade differentiator — Claude Code doesn't offer this.
    """
    name = "env"
    description = "Show environment variables"
    category = "Setup"

    CASCADE_PREFIX = "CASCADE_"
    HEP_VARS = ["SCRAM_ARCH", "CMSSW_BASE", "X509_USER_PROXY"]
    KNOWN_API_KEYS = [
        "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", 
        "GLM_API_KEY", "MINIMAX_API_KEY", "MOONSHOT_API_KEY",
        "DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY", "XAI_API_KEY",
        "XIAOMI_API_KEY"
    ]

    async def execute(self, ctx: CommandContext, args: str) -> None:
        lines = ["[bold]Environment[/bold]\n"]
        found_any = False

        # 1. API Keys — in .env definition order (KNOWN_API_KEYS list order)
        for key in self.KNOWN_API_KEYS:
            val = os.environ.get(key)
            if val:
                found_any = True
                lines.append(f"  [magenta]{key}[/magenta] = {self._redact(val)}")

        # 2. HEP vars (if present)
        for key in self.HEP_VARS:
            val = os.environ.get(key)
            if val:
                found_any = True
                lines.append(f"  [yellow]{key}[/yellow] = {val}")

        # 3. Cascade config vars — always at the bottom
        cascade_vars = sorted(
            (k, v) for k, v in os.environ.items()
            if k.startswith(self.CASCADE_PREFIX)
        )
        for key, val in cascade_vars:
            found_any = True
            display = self._redact(val) if self._is_sensitive(key) else val
            lines.append(f"  [#0087ff]{key}[/#0087ff] = {display}")

        if not found_any:
            lines.append("  [dim]No CASCADE_*, API Keys, or HEP vars found.[/dim]")

        await ctx.output_rich("\n".join(lines))

    def _is_sensitive(self, key: str) -> bool:
        k = key.upper()
        return "KEY" in k or "TOKEN" in k or "SECRET" in k

    def _redact(self, val: str) -> str:
        if len(val) <= 7:
            return "****"
        return f"{val[:3]}****{val[-4:]}"
