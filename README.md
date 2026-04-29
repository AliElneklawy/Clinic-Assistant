# MediCare AI

An AI-powered clinic assistant that combines:

- Medical Q&A with retrieval + web fallback
- Appointment scheduling on Google Calendar
- Diabetes risk classification
- Drug information lookup (use cases + side effects)
- Multi-channel access (Web API, Telegram bot, CLI)

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [API Endpoints](#api-endpoints)
- [Environment Variables](#environment-variables)
- [Getting Started](#getting-started)
- [Run Modes](#run-modes)
- [Docker](#docker)
- [Data and Persistence](#data-and-persistence)
- [Knowledge Base and Crawling](#knowledge-base-and-crawling)
- [Dependency Wiring (Important)](#Dependency-Wiring-(Single-Composition-Root))
- [Disclaimer](#disclaimer)

---

## Overview

Clinic Assistant is a modular Python backend for healthcare assistant workflows.  
It routes user requests through an LLM agent with tools for search, booking, drug lookup, and ML inference.

The system supports:

- **FastAPI web backend** + static web UI
- **Telegram bot** with reminders and follow-up interactions
- **CLI interface** for terminal interaction
- **Background email reminders** for upcoming appointments

---

## Key Features

### 1) AI Medical Assistant (RAG + Web)
- Answers medical questions using a local knowledge base indexed with FAISS.
- Uses Cohere embeddings and optional Cohere reranking.
- Automatically falls back to Tavily web search when local relevance is low.
- Returns responses with source snippets/references.

### 2) Appointment Management
- Lists available appointment slots from Google Calendar.
- Books appointments with overlap checks and slot validation.
- Cancels appointments by event ID.
- Persists appointment records in SQLite.
- Creates shareable “Add to Google Calendar” links.

### 3) Diabetes Risk Prediction
- Accepts structured patient health inputs.
- Performs preprocessing and feature engineering.
- Runs a trained ML model (`joblib`-loaded).
- Returns probability and diagnosis text.

### 4) Drug Information Lookup
- Searches DailyMed by drug name.
- Extracts:
  - Use cases
  - Side effects
- Cleans and returns section text from official label XML.

### 5) Telegram Bot Capabilities
- Conversational health assistant over Telegram.
- Commands:
  - `/start`
  - `/help`
  - `/add_content` (admin-only)
- Scheduled notifications:
  - Periodic health tips from local facts DB
  - Appointment confirmation prompts with inline actions

### 6) Email Reminder Service
- Sends appointment reminder emails using Gmail SMTP SSL.
- Uses both plaintext and HTML templates.
- Marks reminder status in DB to avoid duplicates.
- Runnable as a standalone background process.

### 7) Caching and History
- Redis semantic cache for repeated queries (configurable TTL and distance threshold).
- SQLite chat history via `SQLChatMessageHistory`.
- Session-aware user IDs in web app using FastAPI sessions.

---

## Architecture

High-level flow:

1. User sends query (Web API / Telegram / CLI)
2. `QueryHandlerAgent` decides tool usage
3. Tool layer calls domain services:
   - Search (RAG + Web)
   - Calendar
   - Drug service
   - Diabetes classifier
   - Email service (for reminders)
4. Services read/write persistent state (SQLite, FAISS index, optional Redis)

---

## Project Structure

```text
src/
  agents/
    base_agent.py
    query_handler_agent.py
    tools.py
  api/
    main.py
    endpoints.py
    dependencies/
    static/index.html
  services/
    calendar/
    search/
    ml/
    email/
    database/
    cache/
  rag/
    rag_system.py
  embeddings/
  models/
  settings/
  scripts/
  tg_bot.py
  cli.py
  container.py
data/
  content/
  medical_facts.json
```
## Tech Stack

- **Language**: Python
- **API**: FastAPI
- **LLM / Orchestration**: LangChain + Cohere
- **Vector DB**: FAISS
- **Web Search**: Tavily
- **Calendar Integration**: Google Calendar API
- **Messaging**: python-telegram-bot
- **Database**: SQLite
- **Cache**: Redis (semantic cache via RedisVL)
- **ML**: scikit-learn + joblib
- **Containerization**: Docker + Docker Compose
- **Package Manager**: uv

## API Endpoints

### Chat

- `POST /chat`  
  Chat with the assistant.

### Diabetes

- `POST /predict_diabetes`  
  Predict diabetes risk from structured health data.

### Appointments

- `GET /list_available_slots`  
  List available time slots.
- `POST /book_appointment`  
  Book appointment.
- `POST /cancel_appointment`  
  Cancel by `event_id`.

### Drug Info

- `GET /drug_info?drug_name=<name>`  
  Fetch use cases and side effects.

### Session

- `GET /me`  
  Returns current session user ID.

## Environment Variables

Create a `.env` in project root.

### Required

- `COHERE`
- `TAVILY_SEARCH`
- `TELEGRAM_BOT_TOKEN`
- `ADMINS` (comma-separated Telegram user IDs)
- `SENDER_EMAIL`
- `GMAIL_APP_PASSWORD`
- `SESSION_SECRET_KEY`

### Optional / Defaulted

- `REDIS_URL` (default: `redis://localhost:6379`)

### Also required for calendar auth files (root)

- `creds.json`
- `token.json` (generated after auth flow)

### Optional for scrapegraph crawler mode

- `SGAI`

## Getting Started

### 1) Clone and install

```bash
git clone https://github.com/AliElneklawy/Clinic-Assistant.git
cd Clinic-Assistant
uv sync
```

## 2) Configure Environment

- Add `.env` file with the required variables.
- Place `creds.json` for Google Calendar OAuth.

## 3) Authenticate Calendar (One-time Setup)

Run the following command to authenticate with Google Calendar. This will generate a `token.json` file:

```bash
uv run python -m src.scripts.auth_calendar
```


Run Modes
---------

### CLI Mode

```bash
uv run python -m src.cli
```

### FastAPI Application

Serves the static UI at /. Run with:

```bash
uv run uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

### Telegram Bot

```bash
uv run python -m src.tg_bot
```

### Email Reminder Service

```bash
uv run python -m src.services.email.email_service
```

### Docker

Build and run all services using Docker Compose:

```bash
docker compose up --build
```

**Defined Services:**

*   cli
    
*   telegram-bot
    
*   email\_service
    
*   api (published on port 8000)
    

Data and Persistence
--------------------

*   **SQLite Database**: data/database/clinic.db(Stores appointments, bot subscribers, and medical facts)
    
*   **Chat History**: data/database/chat\_history.db
    
*   **FAISS Indexes**: data/indexes/
    
*   **Logs**: logs/
    
*   **Medical Content**: data/content/
    

Knowledge Base and Crawling
---------------------------

*   The main knowledge base content is loaded from data/content/medical\_data.txt.
    
*   You can append or update indexed content using the provided RAG utilities and scripts.
    
*   An async crawler is available for domain crawling and content export (with configurable depth and rate limiting).
    

### Useful Scripts

*   src/scripts/update\_kb.py
    
*   src/scripts/insert\_facts.py
    
*   src/crawler.py
    

## Dependency Wiring (Single Composition Root)

To avoid service drift, all runtime dependencies must be created in one place: `src/container.py`.

### Rule
- `src/container.py` is the **only** module that constructs concrete services (LLM, RAG, Calendar, DB, Cache, Email, Search, ML).
- API dependency providers in `src/api/dependencies/` must **resolve** already-wired objects/factories, not build new service graphs.
- Entrypoints (`src/api/main.py`, `src/cli.py`, `src/tg_bot.py`) should consume dependencies through this shared wiring path.

### Why
- Prevents duplicated initialization logic across API/CLI/Bot.
- Keeps behavior consistent (same config, same service implementations).
- Reduces regressions when adding/replacing a dependency.

### Practical guidance
- If adding a new service, wire it in `src/container.py` first.
- Reuse that wiring from dependency providers instead of re-instantiating.
- Avoid module-level “hidden” singletons unless lifecycle is explicitly documented.

##  Disclaimer
This project is for informational and workflow-assistance purposes.
It does not replace professional medical diagnosis, treatment, or emergency care.
