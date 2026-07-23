# Pokemon Lakehouse

### A Databricks Lakehouse for Pokémon TCG Metagame Analytics

Pokemon Lakehouse is a personal data engineering project that collects official Pokémon Trading Card Game tournament results and deck compositions, stores them in Delta Lake, and analyzes metagame trends, deck archetypes, similarity, and deck novelty.

The project is also a practical learning environment for Databricks, Apache Spark, Delta Lake, Medallion Architecture, feature engineering, and machine learning.

## Goals

* Build a production-oriented Lakehouse on Databricks
* Practice Bronze, Silver, and Gold data modeling
* Collect official tournament and deck data incrementally
* Preserve raw source data for reproducibility
* Analyze card usage and tournament trends
* Classify deck archetypes from card composition
* Detect novel and innovative deck constructions
* Build Databricks SQL dashboards
* Document architectural decisions using ADRs

## Architecture

```text
Pokémon Official Websites
        │
        ├── Tournament Result API
        └── Deck Print HTML
                 │
                 ▼
        Bronze — Raw source data
                 │
                 ▼
        Silver — Parsed and normalized data
                 │
                 ▼
        Gold — Analytics and ML features
                 │
        ┌────────┴─────────┐
        ▼                  ▼
Databricks SQL         Machine Learning
Dashboards             Archetypes / Novelty
```

See [docs/architecture.md](docs/architecture.md) for details.

## Current Data Model

### Bronze

* `pokemon.bronze.event_result_raw`
* `pokemon.bronze.deck_raw`
* `pokemon.bronze.scrape_log`

### Silver

* `pokemon.silver.tournaments`
* `pokemon.silver.tournament_results`
* `pokemon.silver.decks`
* `pokemon.silver.deck_cards`

### Gold

* `pokemon.gold.card_usage`
* `pokemon.gold.deck_registry`
* `pokemon.gold.deck_pokemon_features`
* `pokemon.gold.deck_similarity`
* `pokemon.gold.deck_archetypes`
* `pokemon.gold.archetype_catalog`
* `pokemon.gold.archetype_cluster_mapping`
* `pokemon.gold.v_deck_archetypes_named` (view)

Planned:

* `pokemon.gold.archetype_summary`
* `pokemon.gold.deck_novelty`
* `pokemon.gold.innovative_decks`

## Repository Structure

```text
pokemon-lakehouse/
├── README.md
├── docs/
│   ├── architecture.md
│   ├── operation_workflow.md
│   ├── adr/
│   └── migration_plan/
├── notebooks/
│   ├── 00_migration/     # v1 → v2 schema migration (one-time)
│   ├── 01_ingest/        # Bronze: API / HTML ingestion
│   ├── 02_silver/        # Silver: parsing and normalization
│   ├── 03_gold/          # Gold: usage, registry, features, similarity
│   ├── 04_ml/            # Archetype clustering and review
│   ├── 05_ops/           # Pipeline run init/finalize/validation
│   ├── 99_analysis/      # Exploratory analysis (not in scheduled workflow)
│   └── _archive/v1/      # Superseded v1 notebooks, kept for reference
├── src/
│   └── pokemon_lakehouse/
└── scripts/
```

## Implemented Pipeline

```text
Tournament Result API
        ↓
pokemon.bronze.event_result_raw   (paginated, full result set per tournament)
        ↓
pokemon.silver.tournaments
pokemon.silver.tournament_results
        ↓
Deck Print HTML
        ↓
pokemon.bronze.deck_raw
        ↓
pokemon.silver.decks
pokemon.silver.deck_cards
        ↓
pokemon.gold.card_usage
pokemon.gold.deck_registry
        ↓
pokemon.gold.deck_pokemon_features
        ↓
pokemon.gold.deck_similarity
        ↓
pokemon.gold.deck_archetypes (per-run cluster assignment, model_run_id + cluster_signature)
        ↓
pokemon.gold.archetype_cluster_mapping ── human review ──▶ pokemon.gold.archetype_catalog
        ↓
pokemon.gold.v_deck_archetypes_named
```

All Gold and archetype-clustering tables are rebuilt atomically on each run via `CREATE OR REPLACE TABLE AS SELECT`, so a failed run never leaves a partially-emptied table. Archetype identity (human-assigned names) is decoupled from the unstable per-run `cluster_id` via a `cluster_signature` and a separate review step (`04_ml/02_review_archetype_mapping.ipynb`), so names survive re-clustering.

## Data Quality Rules

* Tournament API responses are stored before transformation
* Tournament results are fetched across all pages, not truncated at the first page
* Raw HTML is retained in Bronze
* Duplicate Raw responses are detected with SHA-256 hashes and anti-join/MERGE dedup
* Each parsed deck must contain exactly 60 cards
* Deck categories are determined from exact HTML headings
* Basic Energy cards are excluded from general card-usage metrics
* Special Energy cards remain in card-usage analysis
* Deck archetype similarity is based primarily on Pokémon cards
* Gold and archetype-clustering tables are rebuilt atomically (CREATE OR REPLACE TABLE AS SELECT)
* Archetype names are reviewed and stored independently of the unstable per-run cluster ID

## Development Workflow

```text
Issue
  ↓
Architecture Decision Record
  ↓
Implementation
  ↓
Data Quality Validation
  ↓
Commit and Review
```

## Progress

| Area                        | Status      |
| --------------------------- | ----------- |
| Project and Git integration | Complete    |
| Bronze layer                | Complete    |
| Silver tournament pipeline  | Complete    |
| Silver deck pipeline        | Complete    |
| Card parser quality fixes   | Complete    |
| Gold card usage             | Complete    |
| Deck hash / deck registry   | Complete    |
| Deck feature vectors        | Complete    |
| Similarity analysis         | Complete    |
| Archetype classification    | Complete    |
| Archetype naming (human review, stable across reruns) | Complete |
| Atomic Gold/ML rebuilds (CTAS) | Complete |
| Novelty detection           | Planned     |
| Dashboard                   | Planned     |

## Roadmap

### Phase 1 — Data ingestion

* Tournament result API ingestion
* Deck HTML ingestion
* Incremental collection
* Scraping execution logs

### Phase 2 — Silver transformation

* Tournament normalization
* Ranking and deck association
* Deck-card parsing
* Data quality validation

### Phase 3 — Gold analytics (Complete)

* Card usage
* Deck registry (deck hashing/dedup)
* Pokémon-based deck features
* Deck similarity

### Phase 4 — Machine learning

* Archetype clustering (Complete)
* Archetype naming via human-reviewed catalog (Complete)
* Novelty scoring (Planned)
* Innovative deck detection (Planned)

### Phase 5 — Productization

* Databricks SQL dashboards
* Scheduled execution
* Monitoring and alerting
* Expanded tournament history

## Why Pokémon TCG?

Pokémon TCG tournament data is a useful data-engineering dataset because it includes:

* Structured and semi-structured source data
* Relationships between tournaments, players, decks, and cards
* Incrementally changing data
* Historical and time-series analysis
* High-dimensional feature engineering
* Similarity and clustering problems
* Novelty and anomaly detection opportunities

## Disclaimer

This project is for personal learning and analysis. It is not affiliated with or endorsed by The Pokémon Company or related organizations. Source websites should be accessed responsibly and with minimal load.
