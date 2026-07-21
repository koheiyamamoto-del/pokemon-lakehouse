# Pokemon Lakehouse Architecture

## 1. Purpose

Pokemon Lakehouse collects official Pokémon Trading Card Game tournament and deck data and transforms it into analytical datasets for:

* Card-usage analysis
* Metagame analysis
* Deck similarity
* Archetype classification
* Novelty detection
* Tournament-performance analysis

The platform is built on Databricks and Delta Lake using Medallion Architecture.

## 2. Architecture Principles

### Raw data is retained

Source JSON and HTML are stored in Bronze before parsing.

This allows Silver data to be regenerated when:

* The parser changes
* The source format changes
* A data-quality issue is discovered
* Additional attributes are required later

### Ingestion and transformation are separated

Ingestion notebooks only collect and preserve source data.

Transformation notebooks parse, normalize, validate, and write Silver or Gold tables.

### Pipelines are idempotent

Repeated execution should not create unwanted duplicate data.

Raw responses are identified using content hashes, and normalized tables are rebuilt or merged using stable keys.

### Data quality is enforced before writing

Examples:

* A parsed deck must contain exactly 60 cards
* API result counts must match parsed result rows
* Card inclusion rates must remain between zero and one
* Required identifiers must not be null

## 3. Medallion Architecture

```text
Official Tournament API
Official Deck HTML
        │
        ▼
┌─────────────────────────────┐
│ Bronze                      │
│ Raw JSON, HTML, logs        │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ Silver                      │
│ Parsed and normalized data  │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ Gold                        │
│ Metrics and ML features     │
└──────────────┬──────────────┘
               │
        ┌──────┴───────┐
        ▼              ▼
Databricks SQL     Machine Learning
```

## 4. Bronze Layer

### `pokemon.bronze.event_result_raw`

Stores raw JSON responses from the tournament-result API.

Important fields:

* `tournament_id`
* `source_url`
* `http_status`
* `payload`
* `response_hash`
* `scraped_at`
* `ingestion_date`

### `pokemon.bronze.deck_raw`

Stores raw HTML from official deck-print pages.

Important fields:

* `deck_code`
* `source_url`
* `payload`
* `response_hash`
* `scraped_at`
* `ingestion_date`

### `pokemon.bronze.scrape_log`

Stores execution results for ingestion processes.

Important fields:

* `run_id`
* `source_type`
* `source_id`
* `request_url`
* `http_status`
* `status`
* `elapsed_ms`
* `error_type`
* `error_message`

## 5. Silver Layer

### `pokemon.silver.tournaments`

One row per tournament.

### `pokemon.silver.tournament_results`

One row per tournament ranking.

Current key:

```text
tournament_id + rank
```

### `pokemon.silver.decks`

One row per official deck code.

The next model version introduces `deck_hash` to identify functionally identical deck compositions.

### `pokemon.silver.deck_cards`

One row per deck, card name, and printing record.

Card quantity is stored in `quantity`; a four-copy card is not expanded into four physical rows.

## 6. Gold Layer

### `pokemon.gold.card_usage`

Stores card-usage metrics across eligible tournament decks.

Basic Energy cards are excluded because:

* Their inclusion is determined largely by deck type
* They may be included in large quantities
* They can dominate general adoption metrics

Special Energy remains included because its use can be strategically meaningful.

### Planned Gold tables

#### `deck_pokemon_features`

Pokémon-only feature representation for each unique deck.

#### `deck_similarity`

Pairwise deck similarity based primarily on Pokémon composition.

#### `deck_archetypes`

Archetype assignment for each deck.

#### `deck_novelty`

Novelty score relative to historical deck compositions.

## 7. Deck Similarity Strategy

Trainer and support cards are often shared across otherwise unrelated archetypes.

Therefore, primary archetype similarity should be calculated from Pokémon cards rather than all cards.

Initial strategy:

```text
Pokémon card name + quantity
```

Possible similarity metrics:

* Weighted Jaccard similarity
* Cosine similarity
* Distance from cluster centroid

## 8. Deck Identity

Official `deck_code` identifies a published deck instance but not necessarily a unique functional composition.

A future `deck_hash` will identify deck composition using:

```text
normalized card name + total quantity
```

The hash excludes:

* Expansion
* Collection number
* Rarity
* Illustration variant

This means functionally identical cards from different printings are treated as the same deck component.

See `docs/adr/ADR-001-deck-hash.md`.

## 9. Notebook Responsibilities

### Setup

* Catalog and schema creation
* Delta-table initialization

### Ingestion

* External API and HTML access
* Raw response preservation
* Hash generation
* Execution logging

### Transformation

* JSON and HTML parsing
* Normalization
* Validation
* Silver-table creation

### Gold

* Business metrics
* Feature engineering
* Analytical datasets

### Analysis

* Exploration
* Validation
* Visualization
* Hypothesis generation

## 10. Current Limitations

* Only a small number of tournament results have been collected
* Scheduled ingestion is not yet implemented
* Official source structures may change without notice
* Card names currently serve as functional card identifiers
* Player identities should not be treated as permanent stable identifiers
* Tournament coverage depends on officially published deck codes

## 11. Future Architecture

```text
Bronze ingestion
        ↓
Silver normalization
        ↓
Deck identity and card master
        ↓
Feature engineering
        ↓
Similarity and clustering
        ↓
Novelty detection
        ↓
Databricks SQL dashboard
```
