# macOS Bootstrap

> Automated setup for fresh macOS installations with Homebrew package management and Python-based configuration.

## 📋 Overview

This project automates the setup of a fresh **Apple Silicon macOS** machine in three phases:

1. **`entrypoint.sh`** bootstraps a temporary repository-local `uv`, ensures local Python is available, and orchestrates the run
2. **`bootstrap_brew.py`** installs packages from the split Brewfiles in `configuration_homebrew/`
3. **`bootstrap_config.py`** applies filesystem, dotfile, and macOS configuration from YAML files

Together, they provision a new Mac with:

- **Command-line tools** (git, wget, curl, fzf, ripgrep, etc.)
- **Programming languages** (Node.js, Python, Go, Rust, Ruby, Java)
- **DevOps tools** (Docker, Kubernetes, Helm)
- **Desktop applications** (VS Code, browsers, productivity apps)
- **System preferences** (Finder, Dock, keyboard settings, etc.)
- **Shell configuration** (Zsh with plugins and custom prompt)
- **Git configuration** (aliases, colors, and useful settings)

## 🏗 Architecture

### Entry Points & Phases

**`entrypoint.sh` (public orchestrator)**
- ✅ Bootstrap a temporary repository-local `uv`
- ✅ Install Python 3.13 through that local `uv`
- ✅ Run the Brewfile phase
- ✅ Launch the Python configuration phase

**`bootstrap_brew.py` (internal Brew phase)**
- ✅ Install or reinstall packages from split Brewfiles in `configuration_homebrew/`
- ✅ Track per-item installation status and logging

**`bootstrap_config.py` (Python config entrypoint)**
- ✅ Parse CLI options and initialize logging
- ✅ Validate the operating system before continuing
- ✅ Load YAML configuration and execute directory, dotfile, and macOS settings phases
- ✅ Support `--skip-*`, `--dry-run`, `--verbose`, and custom config paths

**Domain entrypoints**
- ✅ `bootstrap_directories.py` runs the directories phase standalone
- ✅ `bootstrap_dotfiles.py` runs the dotfiles phase standalone
- ✅ `bootstrap_macos.py` runs the macOS settings phase standalone

### File Structure

```
bootstrap_macos/
├── entrypoint.sh          # Main public entry point / orchestrator
├── bootstrap_brew.py      # Internal Homebrew Brew phase
├── bootstrap_config.py    # Python configuration orchestrator
├── bootstrap_directories.py
├── bootstrap_dotfiles.py
├── bootstrap_macos.py
├── configuration/         # Split YAML configuration by concern
│   ├── directories.yaml
│   ├── dotfiles.yaml
│   ├── macos_defaults/
│   │   ├── stable_*.yaml
│   │   └── community_*.yaml
│   ├── special_commands.yaml
│   └── restart_applications.yaml
├── pyproject.toml         # Python project & dependencies (UV)
├── configuration_homebrew/
│   ├── Brewfile.core      # Essential CLI and shell tooling
│   ├── Brewfile.dev       # Languages, build tools, dev tooling
│   ├── Brewfile.apps      # Desktop applications (casks)
│   ├── Brewfile.mas       # Mac App Store applications
│   └── Brewfile.extra     # Heavy or specialized tools
├── modules/              # Python modules
│   ├── __init__.py
│   ├── utils.py          # Logging, file operations, helpers
│   ├── directories.py    # Directory creation
│   ├── dotfiles.py       # Dotfile management with backup
│   └── macos_settings.py # macOS defaults application
├── dotfiles/             # Dotfile templates
│   ├── .gitconfig
│   ├── .zshrc
│   └── .gitignore_global
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Fresh macOS installation with **Apple Silicon (M1/M2/M3)** - Intel Macs are not supported
- Internet connection
- Administrator access for tools that may prompt during package installation or macOS configuration

### Installation

1. **Clone or download this repository:**
   ```bash
   git clone <repository-url> ~/bootstrap_macos
   cd ~/bootstrap_macos
   ```

2. **Run the bootstrap script:**
   ```bash
   chmod +x entrypoint.sh
   ./entrypoint.sh
   ```

The wrapper will:

- run the Brewfile phase, which can install the permanent Homebrew-managed `uv`
- bootstrap a temporary repository-local `uv` under `.bootstrap-tools/`
- install Python 3.13 through that local `uv`
- launch `bootstrap_config.py` through the temporary local `uv run`

Platform validation is performed by the Python entrypoints (`bootstrap_brew.py` and `bootstrap_config.py`).

3. **Restart your terminal** after completion to apply shell changes

### Command-Line Options

The `entrypoint.sh` entrypoint supports wrapper options for both the Brewfile and Python configuration phases:

```bash
# Show wrapper help
./entrypoint.sh --help

# Skip the Brewfile phase
./entrypoint.sh --skip-brewfile

# Skip specific Python configuration steps
./entrypoint.sh --skip-dotfiles
./entrypoint.sh --skip-macos-settings
./entrypoint.sh --skip-directories

# Dry run (show what would be done)
./entrypoint.sh --dry-run

# Verbose output
./entrypoint.sh --verbose

# Save log to file
./entrypoint.sh --log-file bootstrap.log

# Use custom config
./entrypoint.sh --config my-config.yaml

# Or point to a split configuration directory
./entrypoint.sh --config configuration
```

Wrapper-specific options:

- `--help` / `-h` — show usage without running the bootstrap phases
- `--skip-brewfile` — skip the Brew phase before launching `bootstrap_config.py`
- `--reinstall-existing` — reinstall already-installed Brewfile formulae and casks during the Brewfile phase

All other options shown above are forwarded to `bootstrap_config.py`, which currently supports:

- `--config`
- `--skip-dotfiles`
- `--skip-macos-settings`
- `--skip-directories`
- `--dry-run`
- `--log-file`
- `--verbose`

In addition to the existing console output and optional `--log-file`, the Python bootstrap entrypoints now also write a separate human-readable audit log to `logs/` with timestamped filenames such as:

```text
logs/audit-bootstrap-config-YYYYMMDD-HHMMSS.log
logs/audit-bootstrap-brew-YYYYMMDD-HHMMSS.log
```

These audit logs are designed for later review and compliance-style reporting. They record business-level events in a readable multi-line format, including:

- run start and completion
- configuration load success or failure
- phase started, skipped, completed, or failed
- directory creation outcomes
- dotfile backup and installation outcomes
- macOS setting and special command outcomes
- Brewfile entry install / reinstall / skip / failure outcomes

## 🔧 Customization

### 1. Edit Configuration (`configuration/`)

The default configuration is now split into smaller files in `configuration/`:

- `configuration/directories.yaml`
- `configuration/dotfiles.yaml`
- `configuration/macos_defaults/`
- `configuration/special_commands.yaml`
- `configuration/restart_applications.yaml`

This keeps each concern isolated and easier to maintain. The bootstrap loader also remains backward compatible with the old single-file `config.yaml` format if you pass it explicitly with `--config`.

`special_commands.yaml` supports two formats:
- `command: ["arg1", "arg2", ...]` for safer non-shell execution
- `shell_command: "..."` for explicit shell-based commands when shell features are required

For list-based `command` entries, `~` paths are expanded by the bootstrap before execution.

Example split configuration:

```yaml
# configuration/directories.yaml
- "~/Projects"
- "~/MyFolder"
```

```yaml
# configuration/dotfiles.yaml
- source: "dotfiles/.gitconfig"
  destination: "~/.gitconfig"
  description: "Git configuration"
```

```yaml
# configuration/macos_defaults/stable_finder_visibility.yaml
stable_finder_visibility:
  - domain: "com.apple.finder"
    key: "AppleShowAllFiles"
    type: "bool"
    value: true
    description: "Show hidden files"
```

`macos_defaults` can now be split into multiple YAML files under `configuration/macos_defaults/`. The loader merges them into one combined `macos_defaults` mapping at runtime. For backward compatibility, a single `configuration/macos_defaults.yaml` file is still also supported when using a custom config directory.

You can also still use a monolithic YAML file by passing a custom path:

```bash
./entrypoint.sh --config my-config.yaml
```

### 2. Customize Dotfiles

Edit files in the `dotfiles/` directory:

- **`dotfiles/.gitconfig`** - Update name and email
- **`dotfiles/.zshrc`** - Add custom aliases and functions
- **`dotfiles/.gitignore_global`** - Add patterns to ignore globally

### 3. Modify Brewfiles

Edit the split Brewfiles in `configuration_homebrew/` to add/remove packages:

```ruby
# Add a new CLI tool to Brewfile.core or Brewfile.dev
brew "neovim"

# Add a new application to Brewfile.apps
cask "docker-desktop"

# Comment out unwanted packages in the relevant file
# brew "mysql"
```

### 4. Create Local Overrides

Create `~/.zshrc.local` for personal shell settings that won't be overwritten:

```bash
touch ~/.zshrc.local
echo 'export MY_CUSTOM_VAR="value"' >> ~/.zshrc.local
```

## 📝 What Gets Installed

Installed software is defined by the Brewfiles under `configuration_homebrew/`. The exact package list in your environment is whatever those files contain at execution time.

### CLI Tools
- Essential: git, wget, curl, tree, htop, watch
- Modern replacements: bat (cat), eza (ls), ripgrep (grep), fd (find), duf (df)
- Shell: zsh-completions, zsh-syntax-highlighting, zsh-autosuggestions
- Search: fzf with fd integration

### Development Tools
- **Languages**: Node.js, Python 3.13, Go, Rust, Ruby, Java
- **Package managers**: pnpm, pipx
- **Build tools**: make, cmake

### DevOps & Cloud
- **Containers**: Docker Desktop, kubectl, helm, k9s
- **Cloud**: AWS CLI, GitHub CLI
- **API / debugging**: httpie

### Desktop Applications
- **Browsers**: Chrome, Firefox
- **Development**: VS Code, Docker Desktop
- **Communication**: Slack, Discord, WhatsApp
- **Productivity / window management**: Raycast, AltTab, Amethyst, BetterDisplay, Stats, AppCleaner
- **Media**: VLC, Transmission Remote GUI, Infuse

### Fonts
- Hack

## 🎯 System Preferences Configured

### Finder
- Show hidden files and all extensions
- Display full path in title bar
- Use list view by default
- Show ~/Library folder

### Dock
- 48px icon size
- Auto-hide with no delay
- No recent applications

### Keyboard
- Fast key repeat (2ms)
- Disable auto-correct and smart quotes

### Screen
- Save screenshots to ~/Screenshots (PNG, no shadow)
- Require password immediately after sleep

### Trackpad
- Enable tap to click

## 🐍 Python with UV

The Python portion of the project is managed with `uv` and defined in `pyproject.toml`.

- Project name: `macos-bootstrap`
- Current Python requirement: **3.13+**
- Current runtime dependency: `PyYAML`

### Why Python for Configuration?

1. **Better Error Handling**: Try-except blocks with detailed error messages
2. **Structured Configuration**: YAML files that are easy to read and validate
3. **Modular Design**: Separate modules for different concerns
4. **Type Safety**: Type hints for better IDE support
5. **Testability**: Easy to unit test individual components
6. **Extensibility**: Simple to add new features

### Why UV Package Manager?

1. **⚡ Fast**: 10-100x faster than pip for dependency resolution
2. **🔒 Reproducible**: Lockfile (uv.lock) ensures consistent environments
3. **🎯 Modern**: Uses pyproject.toml (PEP 621 standard)
4. **📦 Automatic**: No manual dependency installation needed
5. **🔄 Drop-in**: Compatible with existing Python tooling

For bootstrapping, the project now downloads a temporary repository-local `uv` into `.bootstrap-tools/` instead of requiring `uv` to exist globally up front. The Brewfile phase can still install the permanent Homebrew-managed `uv` later as part of the machine setup.

### Python Module Overview

- **`utils.py`**: Logging, path expansion, backups, command execution
- **`directories.py`**: Safe directory creation with existence checks
- **`dotfiles.py`**: Dotfile installation with automatic backup
- **`macos_settings.py`**: Apply macOS defaults with validation

These modules are wired into the active `bootstrap_config.py` execution path and can also be exercised in dry-run mode.

For safety, configuration-driven commands should prefer structured argument lists over raw shell strings. Shell execution should be treated as an explicit escape hatch rather than the default.

## 🔄 Updating & Maintenance

### Update All Packages
```bash
brew update && brew upgrade && brew cleanup
```

Or use the alias:
```bash
update
```

### Re-run Bootstrap
The bootstrap is idempotent - safe to run multiple times:
```bash
cd ~/bootstrap_macos
./entrypoint.sh
```

For Homebrew formulae and casks in the Brewfile, re-running the bootstrap will install missing items and skip already-installed ones by default.

If you want to force reinstallation of already-managed formulae and casks to repair drift, run:

```bash
./entrypoint.sh --reinstall-existing
```

### Brewfile Logs

The Brewfile phase writes detailed logs to `logs/` using timestamped filenames such as:

```text
logs/brew-install-YYYYMMDD-HHMMSS.log
```

These logs include command execution details, per-item outcomes, and a summary of installed, reinstalled, skipped, failed, or unparsed entries.

### Backup Current Brewfile
Generate a Brewfile from your current system:
```bash
brew bundle dump --file=~/Brewfile-backup --force
```

## 🛠 Useful Shell Aliases

Defined in `dotfiles/.zshrc`:

```bash
# Navigation
ll          # List files in long format
la          # List all files including hidden
..          # Go up one directory

# Git
gs          # git status
ga          # git add
gc          # git commit
glog        # git log with graph

# Docker & Kubernetes
d           # docker
dc          # docker compose
k           # kubectl

# Network
myip        # Show public IP
localip     # Show local IP

# Utilities
cleanup     # Remove .DS_Store files
update      # Update Homebrew packages
```

## 🐛 Troubleshooting

### Python Dependencies Not Installing
UV automatically manages dependencies. If you encounter issues:
```bash
# Sync dependencies manually
uv sync

# Or reinstall UV
brew reinstall uv
```

### Permission Errors
Some macOS settings require sudo. The script will prompt when needed.

### Shell Changes Not Applied
Restart your terminal or run:
```bash
source ~/.zshrc
```

### Verbose Logging
Enable debug output:
```bash
./entrypoint.sh --verbose --log-file debug.log
```

## 📦 Manual Steps

Some things still require manual setup:

1. **Sign in to App Store** and iCloud
2. **Configure SSH keys**:
   ```bash
   ssh-keygen -t ed25519 -C "your.email@example.com"
   ```
3. **Set up Git user** (if not done in .gitconfig):
   ```bash
   git config --global user.name "Your Name"
   git config --global user.email "your.email@example.com"
   ```
4. **Configure applications** (Slack, VS Code extensions, etc.)
5. **Privacy settings** in System Preferences

## 🧪 Testing

### Dry Run Mode
Test without making changes:
```bash
./entrypoint.sh --dry-run
```

### Skip Specific Steps
```bash
# Skip the Homebrew/Brewfile phase
./entrypoint.sh --skip-brewfile

# Only run the Python configuration phases
./entrypoint.sh --skip-dotfiles --skip-macos-settings --skip-directories
```

### Verify Python Setup
```bash
uv run bootstrap_config.py --help
```

This verifies the Python entrypoint and configuration workflow.

### Validate Shell Wrapper Help

```bash
./entrypoint.sh --help
```

### Validate the Brewfile Phase Independently

```bash
python3 bootstrap_brew.py
```

> Note: there is currently no `tests/` directory in this repository, so automated test commands should be added together with a test suite.

## 📚 Resources

- [Homebrew Documentation](https://docs.brew.sh/)
- [Homebrew Bundle](https://github.com/Homebrew/homebrew-bundle)
- [macOS defaults Commands](https://macos-defaults.com/)
- [UV Documentation](https://docs.astral.sh/uv/)
- [Python YAML Documentation](https://pyyaml.org/)

## 🤝 Contributing

Customize this bootstrap for your needs:

- Add applications to the files in `configuration_homebrew/`
- Create new Python modules in `modules/`
- Add system preferences to files in `configuration/macos_defaults/`
- Share your configurations with the team

## 📄 License

This bootstrap solution is open source. Modify and distribute as needed.

---

**Happy bootstrapping with Python! 🐍🎉**
