#!/usr/bin/env bash
source "$(poetry env info --path)/bin/activate"
echo "Using Python $(python --version)"
echo "Using Node.js $(node --version)"
