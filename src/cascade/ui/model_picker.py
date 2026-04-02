from __future__ import annotations

import os
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option
from textual.containers import Vertical
from textual import on

from cascade.commands.model.model import PROVIDER_CATALOG


class ModelPickerScreen(ModalScreen[dict]):
    """Interactive model selection overlay."""

    def __init__(self, current_provider: str, current_model: str):
        super().__init__()
        self.current_provider = current_provider
        self.current_model = current_model
        self.choices = []

    def compose(self) -> ComposeResult:
        # Build options
        list_options = []
        for prov_key, prov_info in PROVIDER_CATALOG.items():
            api_key = os.getenv(prov_info["env_key"], "")
            key_status = "[#00d7af]✓[/]" if api_key else "[dim]✗[/]"
            for m in prov_info["models"]:
                is_current = (prov_key == self.current_provider and m["id"] == self.current_model)
                marker = " [bold #00d7af]← current[/]" if is_current else ""
                
                prov_str = f"{prov_info['display']} {key_status}"
                model_str = f"{m['label']} [dim]({m['id']})[/]{marker}"
                
                # We use fixed widths to simulate a table
                display = f"{prov_str:<25} {model_str:<50} {m['price']}"
                
                self.choices.append({
                    "provider": prov_key,
                    "model": m["id"],
                    "display": f"{prov_info['display']} / {m['label']}"
                })
                
                list_options.append(Option(display, id=f"opt_{len(self.choices)-1}"))

        with Vertical(id="model-picker-container"):
            yield Static(
                "[bold #5fd7ff]Select model[/bold #5fd7ff]\n"
                "[dim]Switch between AI models. Applies to this session.\n"
                "Provide custom picks with [bold]/model <prov> <id>[/].[/dim]\n",
                id="model-picker-header"
            )
            yield OptionList(*list_options, id="model-list")
            yield Static("[dim]↑↓ navigate • Enter confirm • Esc cancel[/dim]", id="model-picker-footer")

    @on(OptionList.OptionSelected)
    def handle_selected(self, event: OptionList.OptionSelected) -> None:
        idx = int(event.option.id.split("_")[1])
        choice = self.choices[idx]
        self.dismiss(choice)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)
