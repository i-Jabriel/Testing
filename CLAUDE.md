# CLAUDE.md

This file provides guidance to Claude AI assistants when working with this repository.

---

## Repository Overview

- **Repository**: `i-Jabriel/Testing`
- **Remote**: `http://local_proxy@127.0.0.1:23718/git/i-Jabriel/Testing`
- **Status**: Newly initialized — no source code has been committed yet. This file serves as the foundational documentation and should be updated as the project evolves.

---

## Git Workflow

### Branch Naming Convention

All Claude-driven development branches must follow this pattern:

```
claude/<short-description>-<session-id>
```

Examples:
- `claude/add-claude-documentation-Evth0`
- `claude/fix-authentication-bug-Xy3kP`
- `claude/refactor-api-client-Rm9Tz`

**Never push directly to `main` or `master` without explicit user permission.**

### Pushing Changes

Always use the `-u` flag when pushing a branch for the first time:

```bash
git push -u origin <branch-name>
```

If a push fails due to network errors, retry with exponential backoff:
- Wait 2s, retry
- Wait 4s, retry
- Wait 8s, retry
- Wait 16s, retry (final attempt)

### Fetching / Pulling

Prefer fetching specific branches:

```bash
git fetch origin <branch-name>
git pull origin <branch-name>
```

Apply the same exponential-backoff retry logic (2s → 4s → 8s → 16s) on network failures.

### Commit Messages

Write clear, descriptive commit messages in the imperative mood:

```
Add user authentication endpoint
Fix race condition in background job scheduler
Refactor database connection pooling
```

- Keep the subject line under 72 characters.
- Use the body to explain *why*, not *what*, when context is non-obvious.
- Reference issue/PR numbers when applicable: `Fix login redirect (#42)`.

---

## Development Workflow

Because this is a new, empty repository, the full development workflow will be defined as the project takes shape. The conventions below should be followed once source files are introduced.

### General Principles

1. **Read before editing**: Always read a file before modifying it. Understand existing code before suggesting changes.
2. **Minimal changes**: Only make changes that are directly requested or clearly necessary. Avoid refactoring surrounding code unless asked.
3. **No over-engineering**: Prefer the simplest solution that satisfies the requirements. Do not add abstractions for hypothetical future needs.
4. **Security first**: Never introduce command injection, XSS, SQL injection, or other OWASP Top 10 vulnerabilities. Validate at system boundaries (user input, external APIs).
5. **Avoid backwards-compatibility hacks**: If something is unused, remove it cleanly rather than leaving commented-out or renamed stubs.

### File Management

- Prefer editing existing files over creating new ones.
- Do not create documentation files (`.md`) unless explicitly requested.
- Do not create helper utilities for one-off operations.

---

## Project Structure

> This section will be populated once source code is committed.

Expected layout (update as the project grows):

```
/
├── CLAUDE.md          # This file
├── README.md          # Human-facing project overview (to be created)
├── src/               # Application source code
├── tests/             # Test suites
├── docs/              # Additional documentation
└── .github/           # GitHub Actions workflows and templates
```

---

## Technology Stack

> To be filled in once the technology choices are made.

| Concern        | Choice |
|----------------|--------|
| Language       | TBD    |
| Framework      | TBD    |
| Package manager| TBD    |
| Test runner    | TBD    |
| Linter         | TBD    |
| Formatter      | TBD    |

---

## Testing

> Update this section once a testing framework is chosen.

### Running Tests

```bash
# Example — replace with actual commands
npm test          # Node.js / JavaScript
pytest            # Python
go test ./...     # Go
cargo test        # Rust
```

### Test Conventions

- Tests should live alongside source code or in a dedicated `tests/` directory (document the chosen approach here).
- All new features should include corresponding tests.
- All tests must pass before a branch is considered ready for review.

---

## Linting and Formatting

> Update this section once linting/formatting tools are configured.

```bash
# Example — replace with actual commands
npm run lint      # ESLint / Biome
npm run format    # Prettier
```

Run linting and formatting checks before committing. Fix all errors; warnings should be reviewed and addressed where reasonable.

---

## Environment Configuration

> Update this section once environment variables are established.

- Copy `.env.example` to `.env` for local development (`.env` is git-ignored).
- Never commit secrets, credentials, or API keys.
- Document all required environment variables in `.env.example` with placeholder values and descriptions.

---

## Code Conventions

> Update this section as conventions emerge in the codebase.

### Naming

- Use descriptive, unambiguous names.
- Follow the conventions of the chosen language/framework (e.g., `camelCase` for JS, `snake_case` for Python).

### Comments

- Only add comments where the logic is not self-evident.
- Do not add docstrings, type annotations, or comments to code you didn't change.

### Error Handling

- Only add error handling for scenarios that can realistically occur.
- Trust internal code and framework guarantees — avoid defensive checks on internal state.
- Validate all inputs at system boundaries.

---

## AI Assistant Guidelines

When working in this repository as a Claude AI assistant:

1. **Clarify before acting**: If a task is ambiguous, ask the user to clarify rather than guessing.
2. **Confirm destructive actions**: Before deleting files, resetting branches, or performing other irreversible operations, confirm with the user.
3. **Stay on your branch**: Develop only on the designated `claude/` branch. Never push to `main`/`master` without explicit permission.
4. **Respect scope**: Only implement what was requested. Do not add extra features, refactors, or "improvements" beyond the stated task.
5. **Update this file**: After making significant structural changes to the repository, update the relevant sections of this `CLAUDE.md`.

---

*Last updated: 2026-03-02 — Initial creation for empty repository.*
