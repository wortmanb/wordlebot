# AI Agent Enhancement for Wordlebot

**Date**: 2025-11-24

## Feature Description

Add an agentic AI capability to the existing Wordlebot project. The AI agent should:
- Suggest guesses based on available data
- Attempt to minimize the number of guesses taken
- Use strategic decision-making beyond simple frequency scoring

## Context from Product Planning

**Mission**: Transform Wordlebot from a passive frequency-based assistant into an intelligent AI-powered strategic solver that minimizes guess counts.

**Key Features Planned**:
1. Information Gain Calculator - entropy-based scoring
2. AI Strategy Core - Claude API integration for strategic reasoning
3. Multi-Step Lookahead Engine - minimax evaluation
4. Explainable AI Interface - display reasoning behind suggestions
5. Strategy Mode Selection - aggressive/safe/balanced modes

**Tech Stack**:
- Current: Python 3.12.7, YAML config, CLI interface
- Planned additions: Claude API (Anthropic), information theory implementation, vault for secrets

## Existing Codebase

The current Wordlebot has:
- `Wordlebot` class (src/wordlebot.py:183) - main application
- `KnownLetters` class (src/wordlebot.py:92) - letter constraint tracking
- COCA frequency-based scoring
- Word filtering based on Wordle feedback
- Command-line interface

## Goal

Build an AI agent capability that transforms Wordlebot from a passive word-ranking tool into an active strategic solver that makes intelligent guess recommendations while explaining its reasoning.
