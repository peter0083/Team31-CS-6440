#!/bin/bash

# Development Environment Setup Script
# ====================================
# Ensures dependencies, generates pyproject.toml, sets up pre-commit hooks, and creates activation script.
# Does NOT create sample application.

set -e

# ANSI colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

print_step() { echo -e "${BLUE}${BOLD}🔧 $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; exit 1; }

# 1. Check Python
print_step "Checking Python 3.11.x..."
if command -v python3.11 >/dev/null 2>&1; then
  PY=python3.11
elif command -v python3 >/dev/null 2>&1 && [[ $(python3 --version) =~ "3.11" ]]; then
  PY=python3
else
  print_error "Python 3.11.x not found. Install via Homebrew: brew install python@3.11"
fi
print_success "Using $($PY --version)"

# 2. Check Poetry
print_step "Checking Poetry..."
if ! command -v poetry >/dev/null 2>&1; then
  print_step "Installing Poetry..."
  curl -sSL https://install.python-poetry.org | $PY -
  export PATH="$HOME/.local/bin:$PATH"
fi
print_success "Poetry $(poetry --version)"

# 3. Check NVM and Node
print_step "Checking NVM..."
if ! command -v nvm >/dev/null 2>&1; then
  print_step "Installing NVM..."
  brew install nvm
  mkdir -p "$HOME/.nvm"
  echo 'export NVM_DIR="$HOME/.nvm"' >> ~/.zshrc
  echo 'source /opt/homebrew/opt/nvm/nvm.sh' >> ~/.zshrc
fi
export NVM_DIR="$HOME/.nvm"
source /opt/homebrew/opt/nvm/nvm.sh 2>/dev/null || print_error "nvm.sh not found"
print_success "NVM loaded"

print_step "Ensuring Node.js 22.x..."
if ! nvm ls 22 >/dev/null 2>&1; then
  nvm install 22
fi
nvm alias default 22 && nvm use default
print_success "Node.js $(node --version)"

# 4. Check TypeScript
print_step "Checking TypeScript..."
if ! command -v tsc >/dev/null 2>&1 || [[ ! $(tsc --version) =~ "5.9" ]]; then
  npm install -g typescript@~5.9.0
fi
print_success "TypeScript $(tsc --version)"

# 5. Generate pyproject.toml if missing
if [ ! -f pyproject.toml ]; then
  print_step "Generating pyproject.toml..."
  cat > pyproject.toml << 'EOF'
[tool.poetry]
name = "development-environment"
version = "0.1.0"
description = "Development environment setup"
authors = ["Developer <developer@example.com>"]

[tool.poetry.dependencies]
python = "^3.11"
fastapi = {extras = ["standard"], version = "0.118.3"}
uvicorn = "^0.32.0"
pydantic = "^2.10.0"

[tool.poetry.group.dev.dependencies]
ruff = "^0.7.4"
mypy = "^1.13.0"
isort = "^5.13.2"
pre-commit = "^3.4.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.ruff.lint]
line-length = 88
select = ["E","W","F","I","B","C4","UP"]
ignore = []

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.mypy]
python_version = "3.11"
warn_return_any = false
warn_unused_configs = true
disallow_untyped_defs = false
check_untyped_defs = false

[tool.isort]
profile = "black"
line_length = 88
multi_line_output = 3
EOF
  print_success "pyproject.toml created with relaxed mypy settings"
else
  print_step "pyproject.toml exists; ensure mypy config is relaxed"
fi

# 6. Install dependencies
print_step "Installing Python dependencies..."
poetry config virtualenvs.in-project true
poetry install --no-root
print_success "Dependencies installed"

# 7. Configure pre-commit with relaxed mypy
print_step "Configuring pre-commit..."
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.7.4
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/mirrors-isort
    rev: 5.13.2
    hooks:
      - id: isort
        args: [--profile=black]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
        args: [--ignore-missing-imports, --no-strict-optional, --allow-untyped-defs]
EOF
print_step "Installing pre-commit CLI and hooks..."
poetry run pip install pre-commit
poetry run pre-commit install
print_success "pre-commit configured with relaxed mypy settings"

# 8. Create activation script
print_step "Creating activation script..."
cat > activate_env.sh << 'EOF'
#!/usr/bin/env bash
# Activate the Poetry environment
source "$(poetry env info --path)/bin/activate"
EOF
chmod +x activate_env.sh
print_success "activate_env.sh created"

# 9. Show activation command
print_success "To activate your environment, run:
  ${BOLD}source ./activate_env.sh${NC}"