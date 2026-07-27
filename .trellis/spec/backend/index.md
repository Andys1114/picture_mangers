# Backend Development Guidelines

> Best practices for backend development in this project.

---

## Overview

This directory contains guidelines for backend development. Fill in each file with your project's specific conventions.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Module organization and file layout | Filled |
| [Database Guidelines](./database-guidelines.md) | ORM patterns, queries, migrations | Filled |
| [Error Handling](./error-handling.md) | Error types, handling strategies | Filled |
| [Quality Guidelines](./quality-guidelines.md) | Code standards, forbidden patterns | Filled |
| [Logging Guidelines](./logging-guidelines.md) | Structured logging, log levels | Filled |

---

## Dev-Environment Gotchas (Python tooling on Windows)

> **Warning**: On zh-CN Windows, console stdout defaults to GBK. Any Python wrapper that pipes child-process output (e.g. root `dev.py`) will crash its forwarding thread with `UnicodeEncodeError` the moment a child prints a non-GBK char (Next.js prints "✓") — the un-drained pipe then wedges the child. Every such script must `stream.reconfigure(encoding="utf-8", errors="replace")` on stdout/stderr up front (guard with `hasattr`), and open child pipes with `encoding="utf-8", errors="replace"`. See `dev.py` header for the reference implementation.

---

## How to Fill These Guidelines

For each guideline file:

1. Document your project's **actual conventions** (not ideals)
2. Include **code examples** from your codebase
3. List **forbidden patterns** and why
4. Add **common mistakes** your team has made

The goal is to help AI assistants and new team members understand how YOUR project works.

---

**Language**: All documentation should be written in **English**.
