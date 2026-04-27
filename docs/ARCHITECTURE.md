# Architecture

## System Overview

```mermaid
flowchart TD
    subgraph CLIENT["Client"]
        A["React Frontend\nTypeScript + Vite + Tailwind"]
    end

    subgraph API["FastAPI Backend"]
        B["Analysis Router\n/analyze-food\n/analyze-recipe"]
        C["Ingest Router\n/ingest-guideline"]
        D["Recipe Router\n/generate-recipe"]
    end

    subgraph PIPELINE["Analysis Pipeline"]
        E["Ingredient Extractor\nClaude"]
        F["Rule Engine\nDeterministic"]
        G["Explanation Generator\nClaude"]
        H["Audit Logger"]
    end

    subgraph RAG["RAG Pipeline"]
        I["PDF Parser\npymupdf4llm"]
        J["Semantic Chunker"]
        K["Embedding Provider\nVoyage AI"]
        L["Vector Retriever\npgvector"]
    end

    subgraph DB["PostgreSQL + pgvector"]
        M[("food_items\nontology tree")]
        N[("diet_rules\nper-diet rules")]
        O[("guideline_chunks\nembeddings")]
        P[("query_audit_log\naudit trail")]
    end

    A --> B & C & D
    B --> E --> F --> G --> H
    F --> M & N
    G --> L --> O
    H --> P
    C --> I --> J --> K --> O
```

---

## Analysis Pipeline — Detailed

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Extractor
    participant Engine
    participant Ontology
    participant Explainer
    participant Audit

    Client->>API: POST /analyze-food {"query": "chicken teriyaki"}
    API->>Extractor: extract_ingredients("chicken teriyaki")
    Extractor->>API: ["chicken", "soy sauce", "sugar", "rice"]

    loop For each ingredient
        API->>Engine: evaluate("soy sauce", "tyramine_free")
        Engine->>Ontology: resolve("soy sauce")
        Ontology->>Engine: food_item_id=42 (fermented_soy)
        Engine->>Engine: lookup rule by food_item_id
        Engine->>API: AVOID (direct rule match)
    end

    API->>API: aggregate verdicts → AVOID
    API->>Explainer: generate_explanation(verdicts, retrieved_chunks)
    Explainer->>API: "Soy sauce is a fermented product..."
    API->>Audit: log_query(query, verdicts, latency)
    API->>Client: FoodAnalysisResponse
```

---

## Rule Engine Resolution

```mermaid
flowchart TD
    A["ingredient: 'cheddar'\ndiet: tyramine_free"] --> B

    B{"Direct name\nmatch?"}
    B -->|yes| C["Return rule verdict\n+ resolution_path: direct_match"]
    B -->|no| D

    D{"Alias\nresolution?"}
    D -->|yes| E["Resolve to canonical\nfood_item_id\nLook up rule by id"]
    E --> F["Return verdict\n+ resolution_path: alias_resolution"]
    D -->|no| G

    G{"Ancestor\ntraversal?"}
    G -->|"cheddar → hard cheese\n→ aged cheese (AVOID)"| H
    H["Return verdict from\nancestor rule\n+ resolution_path: ancestor_traversal"]
    G -->|no match| I

    I["Return UNCERTAIN\nnever SAFE\n+ resolution_path: no_match"]
```

---

## Food Ontology Tree (partial)

```mermaid
flowchart TD
    A["dairy"] --> B["cheese"]
    B --> C["aged cheese\n⚠️ AVOID"]
    C --> D["cheddar"]
    C --> E["parmesan"]
    C --> F["brie"]
    B --> G["fresh cheese\n✅ SAFE"]
    G --> H["ricotta"]
    G --> I["mozzarella"]

    J["fermented products"] --> K["soy products"]
    K --> L["soy sauce\n⚠️ AVOID"]
    K --> M["miso\n⚠️ AVOID"]
    K --> N["tofu\n✅ SAFE"]
```

---

## Database Schema

```mermaid
erDiagram
    food_items {
        int id PK
        string name
        string canonical_name
        int parent_id FK
    }

    food_aliases {
        int id PK
        string alias
        int food_item_id FK
    }

    diet_rules {
        int id PK
        string diet_name
        int food_item_id FK
        string status
        string conditions
        string source_text
    }

    guideline_chunks {
        int id PK
        string diet_name
        string source
        int page
        string text
        vector embedding
        string heading
    }

    query_audit_log {
        int id PK
        string query
        string diet_name
        string overall_verdict
        json ingredient_verdicts
        string explanation
        float latency_ms
        timestamp created_at
    }

    food_items ||--o{ food_items : "parent_id"
    food_items ||--o{ food_aliases : "food_item_id"
    food_items ||--o{ diet_rules : "food_item_id"
```

---

## Verdict Priority

```
AVOID (3)  >  CAUTION (2)  >  UNCERTAIN (1)  >  SAFE (0)
```

Meal verdict = max(ingredient verdicts). One AVOID ingredient = AVOID meal.
Unknown ingredients always return UNCERTAIN, never SAFE.

---

## Ingest Pipeline

```mermaid
flowchart LR
    A["PDF or image upload"] --> B["PDF Parser\npymupdf4llm"]
    B --> C["Markdown text\nwith page numbers"]
    C --> D["Semantic Chunker\n~512 tokens\n~64 token overlap"]
    D --> E["DocumentChunk[]"]
    E --> F["Voyage AI\nEmbedding Provider"]
    F --> G["1024-dim vectors"]
    G --> H["pgvector INSERT\nguideline_chunks"]
    C --> I["Rule Extractor\nClaude structured output"]
    I --> J["DietRule[]"]
    J --> K["PostgreSQL INSERT\ndiet_rules"]
```
