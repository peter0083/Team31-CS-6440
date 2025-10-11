#!/usr/bin/env bash

# Unified Setup Script
#
# Automates back-end (Python/Poetry/pre-commit) and front-end (Node/TS/ESLint/Prettier/Husky)

set -e

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

print_step(){ echo -e "${BLUE}${BOLD}🔧 $1${NC}"; }
print_success(){ echo -e "${GREEN}✅ $1${NC}"; }
print_error(){ echo -e "${RED}❌ $1${NC}"; exit 1; }

# 1. Python & Poetry

print_step "Checking Python 3.11.x..."
if command -v python3.11 &>/dev/null; then PY=python3.11
elif command -v python3 &>/dev/null && [[ $(python3 --version) =~ "3.11" ]]; then PY=python3
else print_error "Python 3.11 required"; fi
print_success "Using $($PY --version)"

print_step "Checking Poetry..."
command -v poetry &>/dev/null || { print_step "Installing Poetry..."; curl -sSL https://install.python-poetry.org | $PY -; export PATH="$HOME/.local/bin:$PATH"; }
print_success "Poetry $(poetry --version)"

# 2. NVM & Node

print_step "Ensuring NVM in ~/.zshrc..."
ZSHRC="$HOME/.zshrc"; SNIP='export NVM_DIR="$HOME/.nvm"'
if ! grep -qF "$SNIP" "$ZSHRC"; then
  cat >>"$ZSHRC" <<'EOF'

# Load NVM
export NVM_DIR="$HOME/.nvm"
[ -s "/opt/homebrew/opt/nvm/nvm.sh" ] && source "/opt/homebrew/opt/nvm/nvm.sh"
[ -s "/opt/homebrew/opt/nvm/etc/bash_completion.d/nvm" ] && source "/opt/homebrew/opt/nvm/etc/bash_completion.d/nvm"

EOF
  print_success "NVM init added"
else
  print_step "NVM already in $ZSHRC"
fi

print_step "Loading NVM..."
export NVM_DIR="$HOME/.nvm"; source "/opt/homebrew/opt/nvm/nvm.sh" &>/dev/null || print_error "nvm not found"
if ! nvm ls 22 &>/dev/null; then nvm install 22; fi
nvm alias default 22; nvm use default
print_success "Node $(node --version)"

# 3. TypeScript

print_step "Checking TypeScript..."
if ! command -v tsc &>/dev/null; then npm install -g typescript@~5.9.0; fi
print_success "TypeScript $(tsc --version)"

# 4. Python project setup

print_step "Generating pyproject.toml if missing..."
if [ ! -f pyproject.toml ]; then
  cat > pyproject.toml <<'EOF'
[tool.poetry]
name="dev-env"
version="0.1.0"

[tool.poetry.dependencies]
python="^3.11"
fastapi="0.118.3"

[tool.poetry.group.dev.dependencies]
ruff="^0.7.4"
mypy="^1.13.0"
isort="^5.13.2"
pre-commit="^3.4.0"
EOF
  print_success "pyproject.toml created"
else
  print_step "pyproject.toml exists"
fi

print_step "Installing Python deps..."
poetry config virtualenvs.in-project true
poetry install --no-root
print_success "Python deps installed"

# 5. Configure Python pre-commit

print_step "Configuring Python pre-commit hooks..."
git config --unset-all core.hooksPath &>/dev/null || true
cat > .pre-commit-config.yaml <<'EOF'
repos:
- repo: https://github.com/charliermarsh/ruff-pre-commit
  rev: v0.7.4
  hooks:
    - id: ruff
      args:
        - --fix
- repo: https://github.com/PyCQA/isort
  rev: 5.13.2
  hooks:
    - id: isort
      args:
        - --profile=black
- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.13.0
  hooks:
    - id: mypy
      args:
        - --ignore-missing-imports
        - --allow-untyped-defs
EOF
poetry run pip install pre-commit
poetry run pre-commit install
print_success "Python pre-commit configured"

# 6. Front-end tooling

print_step "Configuring front-end tooling..."
[ -f package.json ] || npm init -y &>/dev/null

npm install --save-dev eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin eslint-plugin-react eslint-plugin-react-hooks eslint-config-prettier prettier husky lint-staged
print_success "Dev dependencies installed"

# Automate Husky prepare step
print_step "Adding Husky prepare script to package.json..."
npm pkg set scripts.prepare="husky install"
print_success "prepare script added"

print_step "Running npm prepare..."
npm run prepare
print_success "Husky install completed"

if [ ! -f .eslintrc.cjs ]; then
  cat > .eslintrc.cjs <<'EOF'
module.exports = {
  root: true,
  env: { browser: true, node: true, jest: true },
  parser: '@typescript-eslint/parser',
  plugins: ['@typescript-eslint','react','react-hooks'],
  extends: ['eslint:recommended','plugin:@typescript-eslint/recommended','plugin:react/recommended','plugin:react-hooks/recommended','prettier'],
  settings: { react: { version: 'detect' } },
  rules: { 'react/react-in-jsx-scope': 'off' },
};
EOF
  print_success ".eslintrc.cjs created"
fi

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

# Husky & lint-staged (hooks folder is already set up by npm prepare)

print_step "Configuring Husky pre-commit hook..."
git config --unset-all core.hooksPath &>/dev/null || true
mkdir -p .husky
cat > .husky/pre-commit <<'EOF'
#!/usr/bin/env sh
poetry run pre-commit run --files "$@"
npx lint-staged
EOF
chmod +x .husky/pre-commit
print_success "Husky pre-commit configured"

# 7. Activation script

print_step "Creating activate_env.sh..."
cat > activate_env.sh <<'EOF'
#!/usr/bin/env bash
source "$(poetry env info --path)/bin/activate"
echo "Using Node.js $(node --version)"
EOF
chmod +x activate_env.sh
print_success "activate_env.sh created"

print_success "Setup complete! Run 'source ./activate_env.sh' to activate."
