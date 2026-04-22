# ~/.zshrc - Zsh Configuration File

################################################################################
# Environment Variables
################################################################################

# Default editor
export EDITOR='code -w'
export VISUAL='code -w'

# Language
export LANG='en_US.UTF-8'
export LC_ALL='en_US.UTF-8'

# Homebrew
if [[ $(uname -m) == 'arm64' ]]; then
    # Apple Silicon
    eval "$(/opt/homebrew/bin/brew shellenv)"
else
    # Intel
    eval "$(/usr/local/bin/brew shellenv)"
fi

# Add local bin to PATH
export PATH="$HOME/.local/bin:$PATH"

################################################################################
# History Configuration
################################################################################

HISTFILE=~/.zsh_history
HISTSIZE=10000
SAVEHIST=10000

setopt EXTENDED_HISTORY          # Write the history file in the ':start:elapsed;command' format
setopt INC_APPEND_HISTORY        # Write to the history file immediately, not when the shell exits
setopt SHARE_HISTORY             # Share history between all sessions
setopt HIST_EXPIRE_DUPS_FIRST    # Expire a duplicate event first when trimming history
setopt HIST_IGNORE_DUPS          # Do not record an event that was just recorded again
setopt HIST_IGNORE_ALL_DUPS      # Delete an old recorded event if a new event is a duplicate
setopt HIST_FIND_NO_DUPS         # Do not display a previously found event
setopt HIST_IGNORE_SPACE         # Do not record an event starting with a space
setopt HIST_SAVE_NO_DUPS         # Do not write a duplicate event to the history file
setopt HIST_VERIFY               # Do not execute immediately upon history expansion

################################################################################
# Completion System
################################################################################

# Load completion system
autoload -Uz compinit
compinit

# Case-insensitive completion
zstyle ':completion:*' matcher-list 'm:{a-zA-Z}={A-Za-z}'

# Enable menu selection
zstyle ':completion:*' menu select

# Color completion
zstyle ':completion:*' list-colors "${(s.:.)LS_COLORS}"

################################################################################
# Plugins (Homebrew-installed)
################################################################################

# Syntax highlighting (install via: brew install zsh-syntax-highlighting)
if [ -f $(brew --prefix)/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]; then
    source $(brew --prefix)/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
fi

# Auto-suggestions (install via: brew install zsh-autosuggestions)
if [ -f $(brew --prefix)/share/zsh-autosuggestions/zsh-autosuggestions.zsh ]; then
    source $(brew --prefix)/share/zsh-autosuggestions/zsh-autosuggestions.zsh
fi

################################################################################
# Prompt Configuration
################################################################################

# Enable parameter expansion, command substitution, and arithmetic expansion in prompts
setopt PROMPT_SUBST

# Git prompt info
autoload -Uz vcs_info
precmd_vcs_info() { vcs_info }
precmd_functions+=( precmd_vcs_info )
zstyle ':vcs_info:git:*' formats ' (%b)'
zstyle ':vcs_info:*' enable git

# Custom prompt
PROMPT='%F{blue}%~%f%F{green}${vcs_info_msg_0_}%f %F{yellow}❯%f '

################################################################################
# Aliases
################################################################################

# Navigation
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'

# Modern CLI replacements
if command -v eza &> /dev/null; then
    alias ls='eza'
    alias ll='eza -l'
    alias la='eza -la'
    alias lt='eza --tree'
else
    alias ll='ls -lh'
    alias la='ls -lah'
fi

if command -v bat &> /dev/null; then
    alias cat='bat'
fi

# Git aliases
alias g='git'
alias gs='git status'
alias ga='git add'
alias gc='git commit'
alias gp='git push'
alias gl='git pull'
alias gd='git diff'
alias gco='git checkout'
alias gb='git branch'
alias glog='git log --oneline --graph --decorate'

# Development
alias py='python3'
alias pip='pip3'

# System
alias reload='source ~/.zshrc'
alias hosts='sudo $EDITOR /etc/hosts'

# Docker
alias d='docker'
alias dc='docker compose'
alias dps='docker ps'
alias dimg='docker images'

# Kubernetes
alias k='kubectl'
alias kgp='kubectl get pods'
alias kgs='kubectl get services'
alias kgd='kubectl get deployments'

# Network
alias myip='curl -s https://ifconfig.me'
alias localip='ipconfig getifaddr en0'

# Utilities
alias cleanup="find . -type f -name '*.DS_Store' -ls -delete"
alias update='brew update && brew upgrade && brew cleanup'

################################################################################
# Functions
################################################################################

# Create directory and cd into it
mkcd() {
    mkdir -p "$1" && cd "$1"
}

# Extract archives
extract() {
    if [ -f "$1" ]; then
        case "$1" in
            *.tar.bz2)   tar xjf "$1"    ;;
            *.tar.gz)    tar xzf "$1"    ;;
            *.bz2)       bunzip2 "$1"    ;;
            *.rar)       unrar x "$1"    ;;
            *.gz)        gunzip "$1"     ;;
            *.tar)       tar xf "$1"     ;;
            *.tbz2)      tar xjf "$1"    ;;
            *.tgz)       tar xzf "$1"    ;;
            *.zip)       unzip "$1"      ;;
            *.Z)         uncompress "$1" ;;
            *.7z)        7z x "$1"       ;;
            *)           echo "'$1' cannot be extracted via extract()" ;;
        esac
    else
        echo "'$1' is not a valid file"
    fi
}

# Git clone and cd into directory
gcl() {
    git clone "$1" && cd "$(basename "$1" .git)"
}

# Quick search in current directory
search() {
    if command -v rg &> /dev/null; then
        rg "$1"
    else
        grep -r "$1" .
    fi
}

################################################################################
# FZF Configuration
################################################################################

# Setup fzf (install via: brew install fzf)
if command -v fzf &> /dev/null; then
    # Auto-completion
    [[ $- == *i* ]] && source "$(brew --prefix)/opt/fzf/shell/completion.zsh" 2> /dev/null
    
    # Key bindings
    source "$(brew --prefix)/opt/fzf/shell/key-bindings.zsh"
    
    # Use fd for fzf if available
    if command -v fd &> /dev/null; then
        export FZF_DEFAULT_COMMAND='fd --type f --hidden --follow --exclude .git'
        export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
    fi
fi

################################################################################
# Node.js Configuration
################################################################################

# pnpm
export PNPM_HOME="$HOME/Library/pnpm"
case ":$PATH:" in
  *":$PNPM_HOME:"*) ;;
  *) export PATH="$PNPM_HOME:$PATH" ;;
esac

################################################################################
# Custom Local Configuration
################################################################################

# Load local configuration if it exists
if [ -f ~/.zshrc.local ]; then
    source ~/.zshrc.local
fi
