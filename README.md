<div align="center">

# ◆ NextQuest

### Tell it three things you love. Get back a list you'll love next.

NextQuest learns your taste from titles you already adore — across **games, movies,
books, TV series and anime** — and hands back fresh picks, each with a sentence or two
explaining *why* it fits you.

<br>

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)

![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy_2.0-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic_v2-E92063?style=for-the-badge&logo=pydantic&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)

![Tests](https://img.shields.io/badge/tests-35_passing-4ade80?style=flat-square)
![Coverage](https://img.shields.io/badge/LLM_calls-mocked_in_CI-7c6cff?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)

</div>

---

## What it does

You fill in a short questionnaire — up to three favourites per category:

<table>
<tr><td><b>🎮 Games</b></td><td>Hollow Knight · Disco Elysium · Outer Wilds</td></tr>
<tr><td><b>🎬 Movies</b></td><td>Arrival · Blade Runner 2049 · Prisoners</td></tr>
<tr><td><b>📚 Books</b></td><td>Dune · Piranesi · The Road</td></tr>
<tr><td><b>📺 TV Series</b></td><td>Dark · Severance · True Detective</td></tr>
<tr><td><b>🌸 Anime</b></td><td>Steins;Gate · Monster · Vinland Saga</td></tr>
</table>

NextQuest reads the pattern behind those choices — tone, pacing, themes, era, art style —
and answers with new titles you probably haven't seen:

> **Kentucky Route Zero** (2020) · *90% match*
> This game offers a slow, atmospheric narrative that mirrors the dreamlike quality of
> Hollow Knight. Its exploration of themes like reality and the human condition aligns
> well with your appreciation for Disco Elysium's storytelling.
>
> `Narrative` `Indie` `Adventure`

Notice that the reason names *your* titles back to you. That is enforced by the prompt,
not left to chance.

## Screenshots

<div align="center">

**Log in / Sign up** — JWT accounts, username or e-mail

<img src="ScreenShots/LogIn.png" alt="NextQuest log in" width="420">
<img src="ScreenShots/SignUp.png" alt="NextQuest sign up" width="420">

<br><br>

**Your taste** — three favourites per category, saved to your account

<img src="ScreenShots/UsersTaste.png" alt="NextQuest taste questionnaire" width="900">

<br><br>

**The picks** — grouped by category, with match scores, reasons and vibe tags

<img src="ScreenShots/Games.png" alt="Game recommendations" width="900">

<img src="ScreenShots/Movies.png" alt="Movie recommendations" width="900">

<img src="ScreenShots/Books.png" alt="Book recommendations" width="900">

<img src="ScreenShots/TVSeries.png" alt="TV series recommendations" width="900">

<img src="ScreenShots/Animes.png" alt="Anime recommendations" width="900">

<br><br>

**History** — every run stays on the account, with the taste it was based on

<img src="ScreenShots/History.png" alt="NextQuest recommendation history" width="900">

</div>

---

## Why it is built this way

<table>
<tr>
<td width="33%" valign="top">

### 🧠 Structured output
The chain uses
`with_structured_output`, so the model
fills in a Pydantic schema instead of
writing prose. The API never parses
free text and never guesses.

</td>
<td width="33%" valign="top">

### 🔁 Top-up rounds
LLMs quietly under-deliver — ask for
15 titles and you get 10. The engine
counts what's missing per category
and asks again, up to two bounded
rounds, until the answer is complete.

</td>
<td width="33%" valign="top">

### 🧹 Post-processing
Echoes of your own titles, duplicates
and off-topic categories are stripped
before anything is stored, so a bad
model day can't pollute your history.

</td>
</tr>
</table>

Everything else follows from that: **JWT auth** so profiles are per-user, a **history**
table that snapshots the taste each run was based on, and a **frontend with no build
step** so the whole app is one `uvicorn` command.

## Tech stack

| Layer | Choice | Why |
|:--|:--|:--|
| **API** | FastAPI · Uvicorn | Async, typed, free OpenAPI docs |
| **Validation** | Pydantic v2 · pydantic-settings | One schema for requests, responses *and* the LLM contract |
| **Persistence** | SQLAlchemy 2.0 typed ORM | SQLite for zero-setup dev, Postgres in Docker |
| **LLM** | LangChain · langchain-openai | Structured output, optional LangSmith tracing |
| **Auth** | python-jose · passlib | JWT bearer tokens, PBKDF2-SHA256 hashing |
| **Frontend** | Vanilla HTML/CSS/JS | No build step, no `node_modules`, served by FastAPI |
| **Tests** | pytest · Starlette TestClient | 35 tests, offline, no API key needed |

---

## Quick start

```bash
git clone https://github.com/bartuonder/NextQuest.git
cd NextQuest

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # then drop your OpenAI key in it
uvicorn main:app --reload
```

| | |
|:--|:--|
| 🌐 **App** | <http://127.0.0.1:8000> |
| 📖 **Swagger UI** | <http://127.0.0.1:8000/docs> |
| ❤️ **Health** | <http://127.0.0.1:8000/health> |

> **No API key?** The app still boots. Everything works except
> `POST /api/recommendations`, which answers `503`, and the UI shows a *no API key* badge.

### 🐳 Docker

```bash
docker compose up --build
```

Brings up Postgres and the API on <http://localhost:8000>, schema created on startup.
The container reads the same `.env` you use locally, so the OpenAI key doesn't need to be
exported separately — `DATABASE_URL` is the only value compose overrides.

## Configuration

Every setting is an environment variable, read from `.env` or the real environment.
See [`.env.example`](.env.example) for the annotated list.

| Variable | Default | Notes |
|:--|:--|:--|
| `DATABASE_URL` | `sqlite:///./nextquest.db` | Postgres: `postgresql+psycopg://user:pass@host:5432/db` |
| `SECRET_KEY` | `change-me-in-production` | ⚠️ **Change this.** Signs the JWTs |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` | Seven days |
| `OPENAI_API_KEY` | — | `OPENAI_KEY` is accepted too |
| `OPENAI_MODEL` | `gpt-4o-mini` | Any chat model supporting structured output |
| `OPENAI_TEMPERATURE` | `0.8` | |
| `LANGCHAIN_API_KEY` | — | Set it to send traces to LangSmith |
| `CORS_ORIGINS` | `*` | Comma separated |

---

## API

All routes live under `/api`. Everything except `/api/meta` and the two auth entry points
needs an `Authorization: Bearer <token>` header.

| | Method | Path | Purpose |
|:--|:--|:--|:--|
| 🩺 | `GET` | `/health` | Liveness probe |
| ℹ️ | `GET` | `/api/meta` | Categories, sample count, whether the LLM is configured |
| 🔑 | `POST` | `/api/auth/register` | Create an account, returns a token |
| 🔑 | `POST` | `/api/auth/login` | JSON login (username **or** e-mail) |
| 🔑 | `POST` | `/api/auth/token` | OAuth2 password flow, powers Swagger's *Authorize* |
| 👤 | `GET` | `/api/auth/me` | The current user |
| ⭐ | `GET` | `/api/favorites` | Flat list of saved titles |
| ⭐ | `POST` | `/api/favorites` | Add one title |
| ⭐ | `DELETE` | `/api/favorites/{id}` | Remove one title |
| 🎯 | `GET` | `/api/favorites/taste` | Favourites grouped per category |
| 🎯 | `PUT` | `/api/favorites/taste` | Replace the whole profile in one request |
| ✨ | `POST` | `/api/recommendations` | Generate a batch |
| 🕘 | `GET` | `/api/recommendations` | Batch history, newest first |
| 🕘 | `GET` | `/api/recommendations/{id}` | One batch |
| 🗑️ | `DELETE` | `/api/recommendations/{id}` | Delete a batch |

<details>
<summary><b>Worked example — register and generate</b></summary>

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"bartu","email":"bartu@example.com","password":"supersecret1"}' \
  | python -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

curl -s -X POST localhost:8000/api/recommendations \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{
        "taste": {
          "games":     ["Hollow Knight", "Disco Elysium", "Outer Wilds"],
          "movies":    ["Arrival", "Blade Runner 2049", "Prisoners"],
          "books":     ["Dune", "Piranesi", "The Road"],
          "tv_series": ["Dark", "Severance", "True Detective"],
          "animes":    ["Steins;Gate", "Monster", "Vinland Saga"]
        },
        "mood": "slow and atmospheric",
        "per_category": 3
      }'
```

Response (trimmed):

```json
{
  "id": 1,
  "model": "gpt-4o-mini",
  "summary": "You have a taste for slow, atmospheric narratives across various media...",
  "items": [
    {
      "category": "game",
      "title": "Kentucky Route Zero",
      "year": 2020,
      "reason": "This game offers a slow, atmospheric narrative that mirrors the dreamlike quality of Hollow Knight...",
      "match_score": 90,
      "tags": ["Narrative", "Indie", "Adventure"]
    }
  ]
}
```

`taste` is optional — leave it out and NextQuest uses the favourites already saved on the
account. `categories` narrows the run, and `per_category` (1–5) sets how many picks each
category gets.

</details>

---

## Project layout

```
NextQuest/
├── LICENSE                  MIT
├── main.py                  FastAPI app, CORS, lifespan, static mount
├── api/
│   ├── deps.py              DB session, current user, engine injection
│   └── routes/              meta · auth · favorites · recommendations
├── core/
│   ├── config.py            Pydantic settings
│   ├── database.py          Engine, session factory, declarative Base
│   ├── enums.py             The five categories
│   └── security.py          Password hashing and JWTs
├── models/                  SQLAlchemy tables
├── schemas/                 Request, response and LLM output models
├── services/
│   ├── auth.py              Registration and credential checks
│   ├── favorites.py         Favourite CRUD and the 3-per-category rule
│   ├── llm_engine.py        LangChain chain, top-up rounds, post-processing
│   └── recommendations.py   Ties the engine to the history tables
├── web/                     The frontend
├── ScreenShots/             App screenshots used in this README
└── tests/                   35 tests, no network access required
```

### Data model

```
User ──< Favorite                        (max 3 per category)
  └──< RecommendationBatch ──< RecommendationItem
```

Each batch stores the taste snapshot it was generated from, so history entries stay
meaningful even after you change your favourites.

## Tests

```bash
pytest
```

The suite runs against a temporary SQLite file and swaps the LLM for a deterministic
fake, so it never calls OpenAI and needs no API key.

---

<div align="center">

**[MIT](LICENSE) licensed** · built by [@bartuonder](https://github.com/bartuonder)

</div>
