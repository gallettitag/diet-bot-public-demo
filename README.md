# Diet Intelligence Platform

A clinical diet reasoning engine that analyzes food safety against medical dietary
guidelines. Given a natural language food query like "Can I eat chicken teriyaki?",
the system extracts individual ingredients, evaluates each against a deterministic
rule engine backed by a food ontology, and returns a clear verdict with citations
from the original guideline documents.

Built for safety-critical dietary restrictions (e.g., tyramine-free diets for MAO
inhibitor patients), where unknown foods must **never** be classified as safe.

> **Note:** This repository is a public architecture demo. The full production
> implementation is maintained privately. Core algorithmic logic and service
> internals are intentionally stubbed — this repo is intended to demonstrate
> system design, data modeling, and engineering approach.

---

## The Problem

Patients on MAO inhibitor medications must follow strict tyramine-free diets.
Consuming high-tyramine foods can trigger hypertensive crises. The challenge:

- Dietary guidelines are written as PDFs by clinicians, not engineers
- "Aged cheese" is unsafe, but does that cover cheddar? Parmesan? Brie?
- A meal like "chicken teriyaki" contains soy sauce, which is a fermented
  product — but most patients don't know that
- Unknown foods must never be assumed safe — uncertainty must be surfaced explicitly

A naive LLM wrapper fails here. GPT will confidently tell a patient a food is
safe when it doesn't know. This system is designed so that **unknown = UNCERTAIN,
never SAFE**.

---

## Architecture

```
User query ("chicken teriyaki")
  → Ingredient Extraction (Claude)
      → ["chicken", "soy sauce", "sugar", "ginger", "rice"]
  → Rule Engine Evaluation (per ingredient)
      → chicken:    SAFE     (direct rule match)
      → soy sauce:  AVOID    (direct rule match — fermented product)
      → sugar:      SAFE     (direct rule match)
      → ginger:     SAFE     (ontology ancestor traversal)
      → rice:       SAFE     (direct rule match)
  → Verdict Aggregation
      → AVOID (most restrictive verdict wins)
  → Explanation Generation (Claude)
  → Audit Log
```

### Rule Engine Resolution Order

For each ingredient, the engine tries resolution strategies in order:

```
1. Direct name match       → exact lookup in diet_rules table
2. Alias resolution        → canonical name lookup, then rule by food_item_id
3. Ancestor traversal      → walk up ontology tree (cheddar → aged cheese → AVOID)
4. No match                → UNCERTAIN (never returns SAFE for unknown foods)
```

### Verdict Priority

```
AVOID (3)  >  CAUTION (2)  >  UNCERTAIN (1)  >  SAFE (0)
```

The overall meal verdict is always the most restrictive individual ingredient verdict.
This is a deliberate safety-first design decision: a meal with one AVOID ingredient
is an AVOID meal regardless of all other ingredients being SAFE.

---

## Tech Stack

| Layer        | Technology                                    |
|---|---|
| Backend      | Python 3.12, FastAPI (async)                 |
| Database     | PostgreSQL 16 + pgvector                     |
| ORM          | SQLAlchemy 2.0 (async)                       |
| LLM          | Anthropic Claude (claude-sonnet-4-20250514)  |
| Embeddings   | Voyage AI (voyage-3.5-lite, 1024-dim)        |
| PDF Parsing  | pymupdf4llm                                  |
| Frontend     | React 19, TypeScript, Vite, Tailwind CSS     |
| Testing      | pytest, pytest-asyncio, httpx                |
| Deployment   | Railway (Docker + PostgreSQL)                |

---

## Key Design Decisions

### Why a deterministic rule engine instead of pure LLM reasoning?

LLMs hallucinate. In a safety-critical domain where a wrong answer could
trigger a hypertensive crisis, probabilistic reasoning over a context window
is not acceptable for the core safety verdict. The rule engine provides
deterministic, auditable, reproducible results. Claude is used only for:

1. **Ingredient extraction** — parsing natural language food queries
2. **Explanation generation** — producing human-readable verdicts after
   the rule engine has already determined the safety classification

The rule engine never delegates safety decisions to the LLM.

### Why a hierarchical food ontology?

Clinical guidelines say "aged cheese" is unsafe. But patients ask about
cheddar, parmesan, brie, manchego. Without a taxonomy, you need a rule
for every possible food name — which is both unmaintainable and incomplete.

The ontology enables rule inheritance: a rule on "aged cheese" automatically
covers every food item whose ancestor chain includes "aged cheese". New foods
can be added to the taxonomy without adding new rules.

### Why UNCERTAIN instead of defaulting to SAFE?

A patient asking about a food Ironclad has never seen should be told
"we don't know — ask your doctor", not "this is safe". The system is
designed so that incomplete knowledge surfaces as uncertainty, not false
confidence. Every unknown food returns UNCERTAIN with an explicit message
directing the patient to consult their healthcare provider.

### Why pgvector over a dedicated vector database?

The guideline corpus is small enough that pgvector provides sufficient
retrieval performance while keeping the infrastructure simple — one database
instead of two. This avoids the operational complexity of a separate vector
store and keeps the audit trail, rules, ontology, and embeddings in a single
transactional system.

---

## API

| Method | Path                        | Description                              |
|---|---|---|
| `GET`  | `/health`                   | Health check                             |
| `POST` | `/api/v1/analyze-food`      | Analyze a food query (natural language)  |
| `POST` | `/api/v1/analyze-recipe`    | Analyze a list of ingredients directly   |
| `POST` | `/api/v1/generate-recipe`   | Generate a diet-compliant recipe         |
| `POST` | `/api/v1/ingest-guideline`  | Upload a dietary guideline PDF or images |

### Example: Analyze a food

```bash
curl -X POST http://localhost:8000/api/v1/analyze-food \
  -H "Content-Type: application/json" \
  -d '{
    "query": "chicken teriyaki with rice",
    "diet_name": "tyramine_free"
  }'
```

Response:

```json
{
  "query": "chicken teriyaki with rice",
  "diet_name": "tyramine_free",
  "overall_verdict": "avoid",
  "ingredient_verdicts": [
    {"ingredient": "chicken",   "status": "safe"},
    {"ingredient": "soy sauce", "status": "avoid", "source_text": "..."},
    {"ingredient": "rice",      "status": "safe"}
  ],
  "explanation": "This meal should be avoided. Teriyaki sauce contains soy sauce,
                  a fermented product high in tyramine...",
  "citations": [{"chunk_id": "...", "source": "tyramine_guidelines.pdf", "page": 4}]
}
```

---

## Database Schema

```
food_items          — Hierarchical food ontology (self-referential tree + aliases)
diet_rules          — Per-diet ingredient rules (safe/caution/avoid + conditions)
guideline_chunks    — Embedded guideline text for RAG retrieval (pgvector)
query_audit_log     — Full audit trail of every analysis query
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full schema diagrams.

---

## Project Structure

```
diet-bot/
├── src/
│   ├── main.py                 # FastAPI app, middleware, lifespan
│   ├── config.py               # Environment settings (pydantic-settings)
│   ├── database.py             # SQLAlchemy async engine + session factory
│   ├── exceptions.py           # Custom exceptions + global handlers
│   ├── analysis/               # Food & recipe analysis pipeline
│   │   ├── router.py           #   /analyze-food, /analyze-recipe endpoints
│   │   ├── service.py          #   Core analysis orchestration
│   │   ├── schemas.py          #   Request/response Pydantic models
│   │   └── prompts.py          #   Claude prompt templates
│   ├── ingredients/            # Ingredient extraction from natural language
│   │   ├── extractor.py        #   Claude-based extraction with retry logic
│   │   └── schemas.py          #   ExtractionResult model
│   ├── rules/                  # Deterministic diet rule engine
│   │   ├── engine.py           #   Rule evaluation + verdict aggregation
│   │   ├── service.py          #   Rule CRUD operations
│   │   └── models.py           #   DietRule, RuleStatus (SQLAlchemy)
│   ├── food/                   # Food ontology
│   │   ├── service.py          #   Canonical resolution + ancestor traversal
│   │   └── models.py           #   FoodItem (self-referential tree)
│   ├── recipes/                # Recipe generation with compliance loop
│   │   ├── router.py           #   /generate-recipe endpoint
│   │   └── service.py          #   Generation + validation retry loop
│   ├── rag/                    # Retrieval-augmented generation pipeline
│   │   ├── chunker.py          #   Semantic text chunking
│   │   ├── embeddings.py       #   Voyage AI embedding provider
│   │   └── retriever.py        #   pgvector similarity search
│   ├── ingest/                 # Document ingestion pipeline
│   │   ├── router.py           #   /ingest-guideline endpoint
│   │   ├── service.py          #   Ingest orchestration
│   │   ├── pdf_parser.py       #   PDF → markdown (pymupdf4llm)
│   │   └── rule_extractor.py   #   Claude-based structured rule extraction
│   └── audit/                  # Audit logging
│       └── models.py           #   QueryAuditLog (SQLAlchemy)
├── tests/                      # Integration & unit tests (pytest)
├── scripts/
│   ├── seed_food_ontology.py   # Populate food taxonomy hierarchy
│   └── seed_tyramine_rules.py  # Seed tyramine-free diet rules
├── alembic/                    # Database migrations
├── docs/
│   ├── ARCHITECTURE.md         # System diagrams (Mermaid)
│   └── HIPAA_COMPLIANCE_ROADMAP.md
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

---

## Local Development

### Prerequisites

- Python 3.12+
- Docker (for PostgreSQL + pgvector)
- Anthropic API key
- Voyage AI API key

### Setup

```bash
git clone https://github.com/gallettitag/diet-bot-demo
cd diet-bot-demo

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# Add your API keys to .env

docker compose up -d
alembic upgrade head

python3 scripts/seed_food_ontology.py
python3 scripts/seed_tyramine_rules.py

uvicorn src.main:app --reload
```

API docs available at `http://localhost:8000/docs`.

---

## Documentation

- **[Architecture](docs/ARCHITECTURE.md)** — System diagrams, data flow, schema
- **[HIPAA Compliance Roadmap](docs/HIPAA_COMPLIANCE_ROADMAP.md)** — Security gaps and implementation plan

---

## License

MIT
