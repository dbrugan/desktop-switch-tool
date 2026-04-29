#!/usr/bin/env python3
"""Desktop switching TUI using Textual."""

import os
import subprocess
from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, ListView, ListItem, Label, Button, Static
from textual.screen import Screen, ModalScreen

SDDM_CONF = Path("/etc/sddm.conf.d/autologin.conf")
SESSION_DIRS = [
    Path("/usr/share/xsessions"),
    Path("/usr/share/wayland-sessions"),
]


class ConfirmModal(ModalScreen[bool]):
    """Modal to confirm session switch."""

    def __init__(self, session_name: str) -> None:
        self.session_name = session_name
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Container(
            Label(f"Switch to [bold]{self.session_name}[/bold]?"),
            Label("This will restart SDDM and log you out!", classes="warning"),
            Container(
                Button("Cancel", variant="default", id="cancel"),
                Button("Switch", variant="error", id="confirm"),
                classes="button-row",
            ),
            classes="modal-content",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)


class SessionItem(ListItem):
    """A selectable session item."""

    def __init__(self, session_id: str, display_name: str, is_current: bool) -> None:
        self.session_id = session_id
        self.display_name = display_name
        super().__init__()
        if is_current:
            self.add_class("current")

    def compose(self) -> ComposeResult:
        suffix = " [dim](current)[/dim]" if "current" in self.classes else ""
        yield Label(f"[bold]{self.display_name}[/bold]{suffix}")


class DesktopSwitchApp(App):
    """Main application for switching desktop sessions."""

    CSS = """
    Screen {
        align: center middle;
    }

    #main-container {
        width: 60;
        height: auto;
        border: round $primary;
        padding: 1;
    }

    #current-session {
        margin: 1 0;
        padding: 1;
        background: $boost;
        border: round $accent;
    }

    #session-list {
        height: auto;
        max-height: 20;
        border: round $surface;
        margin: 1 0;
    }

    ListItem {
        padding: 0 1;
    }

    ListItem:hover {
        background: $accent;
    }

    ListItem.-selected {
        background: $primary;
    }

    #switch-button {
        margin: 1 0;
        width: 100%;
    }

    .warning {
        color: $error;
        margin: 1 0;
    }

    .button-row {
        layout: horizontal;
        align: center middle;
        margin: 1 0;
    }

    .modal-content {
        width: 50;
        padding: 2;
        border: round $error;
        background: $surface;
        align: center middle;
    }

    #status {
        margin: 1 0;
        height: 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("enter", "switch_selected", "Switch"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.current_session: str | None = None
        self.sessions: list[tuple[str, str]] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Container(
                Label("Current Session:", classes="section-title"),
                Static(id="current-session"),
                Label("Available Sessions:", classes="section-title"),
                ListView(id="session-list"),
                Button("Switch Session", variant="primary", id="switch-button"),
                Static(id="status"),
                id="main-container",
            ),
        )
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_sessions()

    def refresh_sessions(self) -> None:
        self.current_session = get_current_session()
        self.sessions = get_available_sessions()

        current_widget = self.query_one("#current-session", Static)
        if self.current_session:
            name = get_session_display_name(self.current_session)
            current_widget.update(f"[bold]{name}[/bold] ({self.current_session})")
        else:
            current_widget.update("[dim]Unknown[/dim]")

        list_view = self.query_one("#session-list", ListView)
        list_view.clear()
        for session_id, display_name in self.sessions:
            is_current = session_id == self.current_session
            item = SessionItem(session_id, display_name, is_current)
            list_view.append(item)

    def action_switch_selected(self) -> None:
        self._switch_selected()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "switch-button":
            self._switch_selected()

    def _switch_selected(self) -> None:
        list_view = self.query_one("#session-list", ListView)
        if not list_view.children:
            return

        selected = list_view.highlighted_child
        if selected is None:
            return

        session_id = selected.session_id
        display_name = selected.display_name

        def handle_confirm(confirmed: bool | None) -> None:
            if confirmed:
                self.switch_session(session_id, display_name)

        self.push_screen(ConfirmModal(display_name), handle_confirm)

    def switch_session(self, session_id: str, display_name: str) -> None:
        status = self.query_one("#status", Static)

        try:
            set_session(session_id)
            status.update(f"[green]Successfully switched to {display_name}[/green]")
            self.refresh_sessions()
        except Exception as e:
            status.update(f"[red]Error: {e}[/red]")


def get_current_session() -> str | None:
    """Get the current autologin session from SDDM config."""
    if not SDDM_CONF.exists():
        return None

    with open(SDDM_CONF) as f:
        for line in f:
            line = line.strip()
            if line.startswith("Session="):
                return line.split("=", 1)[1].strip()
    return None


def get_available_sessions() -> list[tuple[str, str]]:
    """Get all available sessions from .desktop files."""
    sessions = []

    for session_dir in SESSION_DIRS:
        if not session_dir.exists():
            continue

        for desktop_file in session_dir.glob("*.desktop"):
            session_id = desktop_file.stem
            name = parse_desktop_file(desktop_file)
            sessions.append((session_id, name))

    return sorted(sessions, key=lambda x: x[1])


def parse_desktop_file(path: Path) -> str:
    """Parse a .desktop file and return the Name value."""
    name = path.stem

    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("Name=") and not line.startswith("Name["):
                name = line.split("=", 1)[1].strip()
                break

    return name


def get_session_display_name(session_id: str) -> str:
    """Get display name for a session ID."""
    for session_dir in SESSION_DIRS:
        if not session_dir.exists():
            continue
        desktop_file = session_dir / f"{session_id}.desktop"
        if desktop_file.exists():
            return parse_desktop_file(desktop_file)
    return session_id


def set_session(session_id: str) -> None:
    """Update SDDM config and restart SDDM."""
    if not SDDM_CONF.exists():
        raise FileNotFoundError(f"{SDDM_CONF} not found")

    with open(SDDM_CONF) as f:
        lines = f.readlines()

    updated = False
    for i, line in enumerate(lines):
        if line.strip().startswith("Session="):
            lines[i] = f"Session={session_id}\n"
            updated = True
            break

    if not updated:
        lines.append(f"Session={session_id}\n")

    with open(SDDM_CONF, "w") as f:
        f.writelines(lines)

    result = subprocess.run(
        ["sudo", "systemctl", "restart", "sddm"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to restart SDDM: {result.stderr}")


if __name__ == "__main__":
    app = DesktopSwitchApp()
    app.run()
