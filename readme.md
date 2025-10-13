# Team 31 CS-6440 - Clinical Trial Matcher

[![CI](https://github.com/peter0083/Team31-CS-6440/actions/workflows/ci.yml/badge.svg)](https://github.com/peter0083/Team31-CS-6440/actions/workflows/ci.yml)
[![Pre-commit](https://img.shields.io/badge/pre--commit-passing-brightgreen?logo=pre-commit)](https://github.gatech.edu/jtully7/Team31-CS-6440/actions/workflows/pre-commit.yml)
[![Mypy](https://img.shields.io/badge/mypy-passing-brightgreen?logo=mypy&logoColor=ffffff)](https://github.gatech.edu/jtully7/Team31-CS-6440/actions/workflows/mypy.yml)
[![Ruff](https://img.shields.io/badge/ruff-passing-brightgreen?logo=ruff)](https://github.gatech.edu/jtully7/Team31-CS-6440/actions/workflows/ruff.yml)
[![isort](https://img.shields.io/badge/isort-passing-brightgreen?logo=python)](https://github.gatech.edu/jtully7/Team31-CS-6440/actions/workflows/isort.yml)
[![Coverage](https://img.shields.io/codecov/c/github/jtully7/Team31-CS-6440.svg?logo=codecov)](https://codecov.io/gh/jtully7/Team31-CS-6440)


This project provides a single `setup.sh` script to automate the development environment installation and configuration. It installs and configures the following dependencies:

**Runtime & Tools**
- Python 3.11.x (via Homebrew)
- Poetry (dependency manager)
- NVM (Node Version Manager)
- Node.js 22.x
- TypeScript 5.9.x

**Python Libraries**
- FastAPI 0.118.3
- Uvicorn ^0.32.0
- Pydantic ^2.10.0

**Development & Linting**
- Ruff ^0.7.4 (linter/formatter)
- isort ^5.13.2 (import sorter)
- MyPy ^1.13.0 (static type checker)
- pre-commit ^3.4.0 (Git hook manager)

**Pre-commit Hooks**
- ruff (auto-fix enabled)
- isort (Black profile)
- mypy (ignore missing imports, allow untyped defs)

---

## Git Workflow

Ensure all code passes validation on commit with these steps:

1. Stage your changes:

```bash
git add <file1> <file2> ...
```

2. (Optional) Run hooks manually to catch issues early:

```bash
poetry run pre-commit run --all-files
npx lint-staged
```

3. Commit; Husky will run pre-commit (Ruff, isort, MyPy) and lint-staged (ESLint, Prettier) on staged files:

```bash
git commit -m "[conventional commit tag]: your message"
```

4. Push to remote:

```bash
git push
```

To update hooks after changing `.pre-commit-config.yaml`:

```bash
poetry run pre-commit autoupdate
poetry run pre-commit install --overwrite
```

This ensures every commit meets both back-end and front-end quality standards.

## Usage

1. **Make the setup script executable**
   ```bash
   chmod +x setup.sh
   ```

2. **Run the setup script from project root**
   ```bash
   ./setup.sh
   ```
   This will:
   - Verify or install Python, Poetry, NVM, Node.js, and TypeScript
   - Generate a `pyproject.toml` with project dependencies and dev tools
   - Install Python dependencies via Poetry (`--no-root`)
   - Create `.pre-commit-config.yaml` and install Git hooks
   - Generate `activate_env.sh` for venv activation

3. **Activate the Poetry virtual environment**
   The script outputs a final message, for example:
   ```bash
   To activate your environment, run:
     source ./activate_env.sh
   ```
   Copy and paste that command to enter the venv. Your prompt will change, indicating you’re inside the virtual environment.

4. **Run pre-commit checks manually (optional)**
   ```bash
   poetry run pre-commit run --all-files
   ```
   This runs Ruff, isort, and MyPy against all files without making a commit.

---
## Directory Structure
```
├── setup.sh             # Setup and configuration script
├── activate_env.sh      # Virtual env activation script (generated)
├── pyproject.toml       # Poetry project file (generated)
├── .pre-commit-config.yaml  # pre-commit hooks config (generated)
├── src/                 # Your application code
└── tests/               # Your test files
```

---
## Notes
- The setup script does **not** create sample FastAPI example code. Place your own application code under `src/`.
- If you need to adjust lint or type-check rules, update the `[tool.ruff.lint]`, `[tool.mypy]`, and `[tool.isort]` sections in `pyproject.toml`.
- Ensure your shell configuration (`.zshrc`, etc.) sources NVM as shown in the output of the script.

---

