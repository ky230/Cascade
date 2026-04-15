from cascade.commands.base import BaseCommand, CommandContext
import os


class InitCommand(BaseCommand):
    """Initialize project with CASCADE.md.

    Reference: claude-code src/commands/init.ts (257 lines)
    Claude Code impl: type='prompt', injects a massive prompt (OLD_INIT_PROMPT
    or NEW_INIT_PROMPT with 8-phase workflow) that drives the LLM to analyze
    the codebase and generate CLAUDE.md, CLAUDE.local.md, skills, and hooks.
    Uses AskUserQuestion tool for multi-turn interaction.
    Cascade impl: simplified — writes a static CASCADE.md template with
    HEP-specific fields. Full LLM-driven init requires 'prompt' command
    type which Cascade doesn't support yet (Phase 10+).
    """
    name = "init"
    description = "Initialize project with CASCADE.md"
    category = "Setup"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        cascade_md = os.path.join(os.getcwd(), "CASCADE.md")
        if os.path.exists(cascade_md):
            await ctx.output_rich(
                f"[dim]CASCADE.md already exists at {cascade_md}[/dim]"
            )
            return

        template = (
            "# CASCADE.md\n\n"
            "This file provides guidance to Cascade when working "
            "with code in this repository.\n\n"
            "## Key Decisions\n\n"
            "## Architecture Notes\n\n"
            "## Build & Test Commands\n\n"
            "## HEP Analysis Config\n\n"
            "- Cluster: lxplus / local\n"
            "- CMSSW version: \n"
            "- Dataset: \n"
            "- Analysis framework: \n"
        )
        with open(cascade_md, "w") as f:
            f.write(template)
        await ctx.output_rich(
            f"[#00d7af]Created {cascade_md}[/#00d7af]\n"
            f"[dim]Edit this file to customize Cascade's behavior.[/dim]"
        )
