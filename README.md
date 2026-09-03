# NextQuest

Tell NextQuest up to three titles you already love in each of five categories — games,
movies, books, TV series and anime — and it hands back a curated set of new picks, each
with a short explanation of *why* it fits your taste.

The suggestions come from an OpenAI model driven through LangChain with
[structured output](https://python.langchain.com/docs/concepts/structured_outputs/), so
the API always returns validated JSON rather than prose that has to be parsed.

```
Hollow Knight, Disco Elysium, Outer Wilds   ->   Return of the Obra Dinn, Gris
Arrival, Blade Runner 2049, Prisoners       ->   Ex Machina, Annihilation
Dune, Piranesi, The Road                    ->   The Left Hand of Darkness, The Dispossessed
Dark, Severance, True Detective             ->   The OA, The Terror
Steins;Gate, Monster, Vinland Saga          ->   Paranoia Agent, Made in Abyss
```

---

## Features

- **Taste questionnaire** — three favourites per category, saved per user.
- **LLM recommendations** — a LangChain chain with a Pydantic-validated response schema.
- **Top-up pass** — models routinely return fewer titles than asked for, so the engine
  detects short categories and makes one extra call to fill them in.
- **Post-processing** — echoes of your own titles, duplicates and off-topic categories
  are stripped before anything reaches the database.
- **JWT auth** — register, log in with either your username or e-mail, bearer tokens.
- **History** — every run is stored with the taste snapshot that produced it, so you can
  revisit or delete old batches.
- **Web client** — a dependency-free frontend served by the same app.
- **Docker** — one `docker compose up` for API plus Postgres.

## Tech stack

| Layer | Choice |
|---|---|
| API | FastAPI, Uvicorn |
| Validation & settings | Pydantic v2, pydantic-settings |
| Persistence | SQLAlchemy 2.0 (typed ORM), SQLite or Postgres |
| LLM | LangChain, `langchain-openai`, optional LangSmith tracing |
| Auth | python-jose (JWT), passlib (PBKDF2-SHA256) |
| Frontend | Vanilla HTML/CSS/JS, no build step |
| Tests | pytest, Starlette `TestClient` |

## Quick start

```bash
git clone https://github.com/bartuonder/NextQuest.git
cd NextQuest

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # then put your OpenAI key in it
uvicorn main:app --reload
```

- App: <http://127.0.0.1:8000>
- Swagger UI: <http://127.0.0.1:8000/docs>

With no `OPENAI_API_KEY` the app still boots and everything except
`POST /api/recommendations` works; that endpoint answers `503` and the UI shows a
"no API key" badge.

### Docker

```bash
docker compose up --build
```

That starts Postgres and the API on <http://localhost:8000>, with the schema created on
startup. The container reads the same `.env` you use locally, so the OpenAI key does not
have to be exported separately; `DATABASE_URL` is the one value compose overrides.

## Configuration

Every setting is an environment variable, read from `.env` or the real environment. See
[`.env.example`](.env.example) for the annotated list.

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./nextquest.db` | Postgres: `postgresql+psycopg://user:pass@host:5432/db` |
| `SECRET_KEY` | `change-me-in-production` | **Change this.** Signs the JWTs |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` | Seven days |
| `OPENAI_API_KEY` | — | `OPENAI_KEY` is accepted too |
| `OPENAI_MODEL` | `gpt-4o-mini` | Any chat model with structured output support |
| `OPENAI_TEMPERATURE` | `0.8` | |
| `LANGCHAIN_API_KEY` | — | Set to send traces to LangSmith |
| `CORS_ORIGINS` | `*` | Comma separated |

## API

All routes live under `/api`. Everything except `/api/meta` and the two auth entry points
needs an `Authorization: Bearer <token>` header.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness probe |
| `GET` | `/api/meta` | Categories, sample count, whether the LLM is configured |
| `POST` | `/api/auth/register` | Create an account, returns a token |
| `POST` | `/api/auth/login` | JSON login (username **or** e-mail) |
| `POST` | `/api/auth/token` | OAuth2 password flow, used by Swagger's *Authorize* |
| `GET` | `/api/auth/me` | The current user |
| `GET` | `/api/favorites` | Flat list of saved titles |
| `POST` | `/api/favorites` | Add one title |
| `DELETE` | `/api/favorites/{id}` | Remove one title |
| `GET` | `/api/favorites/taste` | Favourites grouped per category |
| `PUT` | `/api/favorites/taste` | Replace the whole profile in one request |
| `POST` | `/api/recommendations` | Generate a batch |
| `GET` | `/api/recommendations` | Batch history, newest first |
| `GET` | `/api/recommendations/{id}` | One batch |
| `DELETE` | `/api/recommendations/{id}` | Delete a batch |

### Example

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
        "mood": "something slow and atmospheric",
        "per_category": 2
      }'
```

Response (trimmed):

```json
{
  "id": 1,
  "model": "gpt-4o-mini",
  "summary": "You enjoy immersive, thought-provoking narratives with emotional depth...",
  "items": [
    {
      "category": "game",
      "title": "Return of the Obra Dinn",
      "year": 2018,
      "reason": "Like Outer Wilds it hands you a mystery and nothing else...",
      "match_score": 90,
      "tags": ["mystery", "exploration", "puzzle"]
    }
  ]
}
```

`taste` is optional — leave it out and NextQuest uses the favourites already saved on the
account. Optional `categories` narrows the run, and `per_category` (1–5) sets how many
picks each category gets.

## Project layout

```
NextQuest/
├── main.py                  FastAPI app, CORS, lifespan, static mount
├── api/
│   ├── deps.py              DB session, current user, engine injection
│   └── routes/              meta, auth, favorites, recommendations
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
│   ├── llm_engine.py        LangChain chain, top-up pass, post-processing
│   └── recommendations.py   Ties the engine to the history tables
├── web/                     The frontend
└── tests/                   33 tests, no network access required
```

### Data model

```
User ──< Favorite                     (<= 3 per category)
  └──< RecommendationBatch ──< RecommendationItem
```

A batch stores the taste snapshot it was generated from, so history entries stay
meaningful even after you change your favourites.

## Tests

```bash
pytest
```

The suite runs against a temporary SQLite file and swaps the LLM for a deterministic
fake, so it never calls OpenAI and needs no API key.

## Licence

MIT
