# ADR-001: Introduce a Functional Deck Hash

* Status: Accepted
* Date: 2026-07-21
* Decision owners: Pokemon Lakehouse project
* Related tables:

  * `pokemon.silver.decks`
  * `pokemon.silver.deck_cards`
  * `pokemon.silver.tournament_results`

## Context

The official deck code identifies a deck saved or published through the official Pokémon Card Game website.

However, the official deck code is not a reliable identifier for a unique deck composition.

The same functional 60-card deck may have:

* Different official deck codes
* Different card illustrations
* Different rarities
* Different expansion symbols
* Different collection numbers

Using `deck_code` alone would make identical deck compositions appear to be unrelated decks.

The project requires a stable identifier for analyses such as:

* First appearance of a deck composition
* Repeated tournament usage
* Average placement
* Deck similarity
* Archetype classification
* Novelty detection

## Decision

Introduce a `deck_hash` generated from the functional composition of a deck.

The hash input will use:

```text
normalized card_name + aggregated quantity
```

The card entries will be sorted by normalized card name before hashing.

Example canonical representation:

```text
すごいつりざお|2
なかよしポフィン|4
ネストボール|3
ボスの指令|2
```

The complete canonical string will be hashed using SHA-256.

## Card aggregation rule

Before calculating the hash, records with the same normalized card name are aggregated.

Example:

```text
ハイパーボール, expansion A, quantity 2
ハイパーボール, expansion B, quantity 2
```

becomes:

```text
ハイパーボール|4
```

## Why collection number is excluded

Collection number identifies a particular card printing rather than its functional role in the deck.

The same card effect may be printed in:

* Different sets
* Different rarity treatments
* Alternate artwork
* Promotional versions

Including collection number would generate different hashes for decks that are functionally identical during gameplay.

This would reduce the quality of:

* Archetype analysis
* Similarity analysis
* Historical tracking
* Novelty detection

## Why expansion is excluded

Expansion information has the same limitation as collection number.

It describes the physical printing, not the functional card identity used in the deck.

Expansion and collection number will remain in Silver tables for card-printing analysis but will not be included in the functional deck hash.

## Why card name is used

At the current stage, card name is the best available functional card identifier.

It provides:

* Human readability
* Compatibility with current scraped data
* Stable aggregation across printings
* Simple validation and debugging

## Consequences

### Positive

* Identical functional decks share the same identifier
* Multiple official deck codes can map to one composition
* Tournament performance can be aggregated by composition
* Similarity and novelty analysis become more reliable
* Card rarity and illustration differences do not create false deck variants

### Negative

* Two cards with the same name but different effects would collide
* Future card-name formatting changes could alter hashes
* Japanese text normalization becomes part of key generation
* Historical hashes must be regenerated if normalization rules change

## Normalization requirements

Before hashing:

1. Trim leading and trailing whitespace
2. Normalize repeated whitespace
3. Normalize full-width spaces
4. Aggregate quantities by normalized card name
5. Sort by normalized card name
6. Join entries with newline characters
7. Hash the UTF-8 encoded canonical string with SHA-256

## Data-model impact

The following columns will be added:

### `pokemon.silver.decks`

```text
deck_hash STRING
```

### `pokemon.silver.deck_cards`

```text
deck_hash STRING
```

### `pokemon.silver.tournament_results`

```text
deck_hash STRING
```

The official `deck_code` will remain available as a source-system identifier.

## Future considerations

A future official card master may provide a stable functional card identifier.

At that point, the project may evaluate:

```text
functional_card_id + quantity
```

as a replacement for card-name-based hashing.

Changing the hash definition would require a new ADR and a hash-version column such as:

```text
deck_hash_version
```

## Decision summary

Use:

```text
card_name + aggregated quantity
```

Do not use:

```text
expansion
collection_number
rarity
illustration
```

This decision prioritizes functional deck identity over physical card-printing identity.
