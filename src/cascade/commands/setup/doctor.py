from cascade.commands.base import BaseCommand, CommandContext
import subprocess
import shutil
import os


class DoctorCommand(BaseCommand):
    """Run health diagnostics (HEP-aware).

    Reference: claude-code src/commands/doctor/doctor.tsx (7 lines, entry)
    Claude Code impl: loads screens/Doctor.js JSX component with
    full-screen diagnostic UI. Checks: Node version, git, API keys,
    npm, network connectivity.
    isEnabled: () => !isEnvTruthy(DISABLE_DOCTOR_COMMAND)
    Cascade impl: Python text-based diagnostics with HEP-specific
    checks (grid proxy, CMSSW, SCRAM_ARCH) not present in Claude Code.
    """
    name = "doctor"
    description = "Run health diagnostics (HEP-aware)"
    category = "Setup"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        lines = ["[bold]Cascade Doctor[/bold]\n"]

        checks = [
            self._check_python(),
            self._check_git(),
            self._check_cascade_env(),
            self._check_api_keys(),
        ]

        # HEP-specific checks
        if os.getenv("CMSSW_BASE") or shutil.which("voms-proxy-info"):
            checks.extend([
                self._check_grid_proxy(),
                self._check_cmssw(),
            ])
            
        if shutil.which("condor_q"):
            checks.append(self._check_condor())

        for name, ok, detail in checks:
            icon = "[green]✓[/green]" if ok else "[red]✗[/red]"
            lines.append(f"  {icon} {name}: [dim]{detail}[/dim]")

        await ctx.output_rich("\n".join(lines))

    def _check_python(self):
        import sys
        v = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        return ("Python >= 3.11", sys.version_info >= (3, 11), v)

    def _check_git(self):
        ok = shutil.which("git") is not None
        return ("git", ok, shutil.which("git") or "not found")

    def _check_cascade_env(self):
        has_env = os.path.exists(".env")
        return (".env file", has_env, "found" if has_env else "not found in cwd")

    def _check_api_keys(self):
        keys = ["DEEPSEEK_API_KEY", "GLM_API_KEY", "ANTHROPIC_API_KEY",
                "GEMINI_API_KEY", "OPENAI_API_KEY", "XIAOMI_API_KEY", "XAI_API_KEY", "DASHSCOPE_API_KEY"]
        found = [k for k in keys if os.getenv(k)]
        return ("API Keys", len(found) > 0, f"{len(found)}/{len(keys)} configured")

    def _check_grid_proxy(self):
        try:
            r = subprocess.run(
                ["voms-proxy-info", "--timeleft"],
                capture_output=True, text=True, timeout=5
            )
            timeleft = int(r.stdout.strip()) if r.returncode == 0 else 0
            ok = timeleft > 3600
            return ("Grid Proxy", ok,
                    f"{timeleft}s remaining" if ok else "expired or missing")
        except Exception:
            return ("Grid Proxy", False, "voms-proxy-info not available")

    def _check_cmssw(self):
        base = os.getenv("CMSSW_BASE", "")
        return ("CMSSW", bool(base), base or "not set")

    def _check_condor(self):
        try:
            r = subprocess.run(
                ["condor_q"],
                capture_output=True, text=True, timeout=5
            )
            ok = r.returncode == 0
            return ("HTCondor", ok, "available" if ok else "failed to query")
        except Exception:
            return ("HTCondor", False, "not available")
