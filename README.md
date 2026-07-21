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

Planned:

* `pokemon.gold.deck_pokemon_features`
* `pokemon.gold.deck_similarity`
* `pokemon.gold.deck_archetypes`
* `pokemon.gold.archetype_summary`
* `pokemon.gold.deck_novelty`
* `pokemon.gold.innovative_decks`

## Repository Structure

```text
pokemon-lakehouse/
├── README.md
├── docs/
│   ├── architecture.md
│   └── adr/
├── notebooks/
│   ├── 00_setup/
│   ├── 01_ingest/
│   ├── 02_transform/
│   ├── 03_gold/
│   └── 04_analysis/
├── src/
├── sql/
└── tests/
```

## Implemented Pipeline

```text
Tournament Result API
        ↓
pokemon.bronze.event_result_raw
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
```

## Data Quality Rules

* Tournament API responses are stored before transformation
* Raw HTML is retained in Bronze
* Duplicate Raw responses are detected with SHA-256 hashes
* Each parsed deck must contain exactly 60 cards
* Deck categories are determined from exact HTML headings
* Basic Energy cards are excluded from general card-usage metrics
* Special Energy cards remain in card-usage analysis
* Deck archetype similarity is based primarily on Pokémon cards

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
| Deck hash                   | In progress |
| Deck feature vectors        | Planned     |
| Similarity analysis         | Planned     |
| Archetype classification    | Planned     |
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

### Phase 3 — Gold analytics

* Card usage
* Tournament-level usage
* Pokémon-based deck features
* Deck similarity

### Phase 4 — Machine learning

* Archetype clustering
* Archetype naming
* Novelty scoring
* Innovative deck detection

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
