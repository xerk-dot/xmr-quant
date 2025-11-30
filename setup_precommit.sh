#!/bin/bash
# Setup script for pre-commit hooks

echo "Installing pre-commit and dependencies..."
pip install pre-commit ruff mypy

echo "Installing pre-commit hooks..."
pre-commit install

echo "Running pre-commit on all files (first run)..."
pre-commit run --all-files || true

echo ""
echo "✅ Pre-commit hooks installed successfully!"
echo ""
echo "The following hooks will run on every commit:"
echo "  - ruff (linter and formatter)"
echo "  - mypy (type checker)"
echo "  - trailing whitespace removal"
echo "  - end-of-file fixer"
echo "  - YAML validation"
echo "  - large file detection"
echo "  - merge conflict detection"
echo "  - private key detection"
echo ""
echo "To run manually: pre-commit run --all-files"
