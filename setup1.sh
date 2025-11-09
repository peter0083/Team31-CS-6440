#!/usr/bin/env bash

# ================================================================
# Unified Setup Script (Git Bash / Poetry)
# ================================================================
# Automates:
#  - Python backend setup (FastAPI + Poetry + Requests)
#  - Frontend setup (Node.js, TypeScript, ESLint, Prettier, Husky)
#  - Auto-detects ui/ or src/ui/ folders for frontend dependency install
# ================================================================

set -e

# ------------------ Colors ------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
print_step(){ echo -e "${BLUE}${BOLD}?? $1${NC}"; }
print_success(){ echo -e "${GREEN}? $1${NC}"; }
print_error(){ echo -e "${RED}? $1${NC}"; exit 1; }

# ================================================================
# 1??  PYTHON + POETRY SETUP
# ================================================================
print_step "Checking Python 3.11 installation..."

if command -v python3.11.0 &>/dev/null; then
  PYTHON_CMD=python3.11.0
elif command -v python3 &>/dev/null && [[ "$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" == "3.11" ]]; then
  PYTHON_CMD=python3
elif command -v python &>/dev/null && [[ "$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" == "3.11" ]]; then
  PYTHON_CMD=python
else
  print_error "Python 3.11 not found. Please install it first."
fi
print_success "Using $($PYTHON_CMD --version)"

# ================================================================
# 2??  INSTALL POETRY
# ================================================================
print_step "Checking Poetry..."
if ! command -v poetry &>/dev/null; then
  print_step "Installing Poetry..."
  curl -sSL https://install.python-poetry.org | $PYTHON_CMD -
  export PATH="$HOME/.local/bin:$PATH"
else
  print_success "Poetry already installed: $(poetry --version)"
fi

# Configure Poetry to create env inside project
poetry config virtualenvs.in-project true

# ================================================================
# 3??  CREATE dev-env AND INSTALL PYTHON DEPENDENCIES
# ================================================================
print_step "Creating Poetry environment (dev-env)..."

if [ ! -f pyproject.toml ]; then
  cat > pyproject.toml <<'EOF'
[tool.poetry]
name = "dev-env"
version = "0.1.0"
description = "Development environment with FastAPI, Requests, and frontend tools"
authors = ["You <you@example.com>"]

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "0.118.3"
uvicorn = "^0.30.0"
httpx = "^0.27.0"
requests = "^2.32.3"

[tool.poetry.group.dev.dependencies]
ruff = "0.7.4"
mypy = "1.13.0"
isort = "5.13.2"
pre-commit = "3.4.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
EOF
  print_success "pyproject.toml created"
else
  print_step "pyproject.toml already exists   updating dependencies..."
  poetry add requests@^2.32.3
fi

poetry install --no-root
print_success "Python dependencies installed in Poetry env"

# ================================================================
# 4??  CONFIGURE PRE-COMMIT
# ================================================================
print_step "Setting up pre-commit hooks..."
cat > .pre-commit-config.yaml <<'EOF'
repos:
- repo: https://github.com/charliermarsh/ruff-pre-commit
  rev: v0.7.4
  hooks:
    - id: ruff
      args: [--fix]
- repo: https://github.com/PyCQA/isort
  rev: 5.13.2
  hooks:
    - id: isort
      args: [--profile=black]
- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.13.0
  hooks:
    - id: mypy
      args: [--ignore-missing-imports, --allow-untyped-defs]
EOF

poetry run pre-commit install
print_success "Pre-commit configured successfully"

# ================================================================
# 5??  NODE / NVM SETUP
# ================================================================
print_step "Checking NVM..."

if [ -d "$HOME/.nvm" ]; then
  export NVM_DIR="$HOME/.nvm"
  [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
else
  print_step "Installing NVM..."
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
  export NVM_DIR="$HOME/.nvm"
  [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
fi
print_success "NVM installed/loaded"

print_step "Installing Node.js v22..."
nvm install 22
nvm alias default 22
nvm use 22
print_success "Using Node $(node --version)"

# ================================================================
# 6??  FRONTEND TOOLING (Root-level)
# ================================================================
print_step "Installing frontend tooling in root..."
[ -f package.json ] || npm init -y &>/dev/null

npm install --save-dev eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin eslint-plugin-react eslint-plugin-react-hooks eslint-config-prettier prettier husky lint-staged
npm install -g typescript@~5.9.0

# ESLint config
if [ ! -f .eslintrc.cjs ]; then
  cat > .eslintrc.cjs <<'EOF'
module.exports = {
  root: true,
  env: { browser: true, node: true, jest: true },
  parser: '@typescript-eslint/parser',
  plugins: ['@typescript-eslint', 'react', 'react-hooks'],
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react/recommended',
    'plugin:react-hooks/recommended',
    'prettier'
  ],
  settings: { react: { version: 'detect' } },
  rules: { 'react/react-in-jsx-scope': 'off' },
};
EOF
  print_success ".eslintrc.cjs created"
fi

# Prettier config
if [ ! -f .prettierrc ]; then
  cat > .prettierrc <<'EOF'
{
  "singleQuote": true,
  "semi": true,
  "trailingComma": "all",
  "printWidth": 100
}
EOF
  print_success ".prettierrc created"
fi

# Husky setup
print_step "Setting up Husky pre-commit..."
npm pkg set scripts.prepare="husky install"
npm run prepare
mkdir -p .husky
cat > .husky/pre-commit <<'EOF'
#!/usr/bin/env sh
poetry run pre-commit run --files "$@"
npx lint-staged
EOF
chmod +x .husky/pre-commit
print_success "Husky pre-commit hook added"

# ================================================================
# 7??  AUTO-DETECT UI OR SRC/UI FOLDER
# ================================================================
UI_DIR=""
if [ -d "src/ui" ]; then
  UI_DIR="src/ui"
elif [ -d "ui" ]; then
  UI_DIR="ui"
fi

if [ -n "$UI_DIR" ]; then
  print_step "Detected frontend folder: $UI_DIR   setting up dependencies..."
  cd "$UI_DIR"
  if [ -f package.json ]; then
    npm install
    print_success "Dependencies installed in $UI_DIR"
  else
    print_step "No package.json found   initializing new frontend project..."
    npm init -y
    npm install react react-dom
    npm install --save-dev typescript @types/react @types/react-dom vite
    print_success "React/Vite project initialized in $UI_DIR"
  fi
  cd ../..
else
  print_step "No ui or src/ui folder found   skipping frontend setup"
fi

# ================================================================
# 8??  DONE
# ================================================================
print_success "Setup complete!"
echo -e "\n?? To activate your Poetry environment, run:"
echo -e "   poetry shell\n"
echo -e "?? To start FastAPI locally:"
echo -e "   poetry run uvicorn app:app --reload\n"
echo -e "?? If you have a UI project, navigate to ${UI_DIR:-ui} and run:"
echo -e "   npm run dev\n"
