# Desktop Switch Tool

A TUI (Terminal User Interface) for switching SDDM autologin sessions. Built with [Textual](https://textual.textualize.io/).

## Clone and Execute

```bash
# Clone the repository
git clone https://github.com/dbrugan/desktop-switch-tool.git
cd desktop-switch-tool

# Run the TUI
./desktop-switch
```

## Usage

- **Navigate**: Use ↑/↓ arrow keys to select a session
- **Switch**: Press Enter or click "Switch Session"
- **Confirm**: Approve the confirmation dialog to restart SDDM
- **Quit**: Press Q or Escape

**Warning:** Switching sessions restarts SDDM and logs you out.
