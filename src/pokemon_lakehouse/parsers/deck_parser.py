from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup


CATEGORY_NAMES = {
    "ポケモン": "pokemon",
    "グッズ": "goods",
    "ポケモンのどうぐ": "pokemon_tool",
    "サポート": "supporter",
    "スタジアム": "stadium",
    "エネルギー": "energy",
}


def normalize_text(value: str | None) -> str:
    """
    Normalize Japanese and HTML-extracted text.

    Args:
        value: Raw text value.

    Returns:
        Whitespace-normalized string.
    """
    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        value.replace("\u3000", " "),
    ).strip()


def parse_quantity(value: str) -> int | None:
    """
    Parse a card quantity from text.

    Examples:
        "4" -> 4
        "4枚" -> 4
    """
    normalized = normalize_text(value)

    if re.fullmatch(r"\d+", normalized):
        return int(normalized)

    match = re.search(r"(\d+)\s*枚", normalized)

    if match:
        return int(match.group(1))

    return None


def parse_deck_html(
    html: str,
    deck_code: str,
) -> list[dict[str, Any]]:
    """
    Parse a Pokemon deck print-page HTML document.

    Category detection is based only on exact heading-cell matches.
    Card names, image alt text, and surrounding text are not used
    to infer the category.

    Args:
        html: Raw HTML from the official deck print page.
        deck_code: Official deck code.

    Returns:
        One dictionary per distinct card printing.
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")

    cards: list[dict[str, Any]] = []
    current_category: str | None = None

    for row in soup.find_all("tr"):
        cells = [
            normalize_text(
                cell.get_text(" ", strip=True)
            )
            for cell in row.find_all(
                ["th", "td"],
                recursive=False,
            )
        ]

        cells = [
            cell
            for cell in cells
            if cell
        ]

        if not cells:
            continue

        first_cell = cells[0]

        # Category changes only on an exact heading match.
        if first_cell in CATEGORY_NAMES:
            current_category = CATEGORY_NAMES[first_cell]
            continue

        row_text = " ".join(cells)

        excluded_words = [
            "小計",
            "合計",
            "カード名",
            "枚数",
            "エキスパンション",
            "コレクションNo.",
        ]

        if any(
            word in row_text
            for word in excluded_words
        ):
            continue

        if current_category is None:
            continue

        quantity: int | None = None
        quantity_index: int | None = None

        for index, cell in enumerate(
            cells[1:],
            start=1,
        ):
            parsed_quantity = parse_quantity(cell)

            if parsed_quantity is not None:
                quantity = parsed_quantity
                quantity_index = index
                break

        if quantity is None or quantity_index is None:
            continue

        remaining_cells = cells[quantity_index + 1:]

        expansion = (
            remaining_cells[0]
            if len(remaining_cells) >= 1
            else None
        )

        collection_number = (
            remaining_cells[1]
            if len(remaining_cells) >= 2
            else None
        )

        cards.append({
            "deck_code": deck_code,
            "category": current_category,
            "card_name": first_cell,
            "quantity": quantity,
            "expansion": expansion,
            "collection_number": collection_number,
        })

    return cards


def summarize_deck(
    cards: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Calculate simple quality metrics for parsed deck cards.
    """
    total_cards = sum(
        int(card["quantity"])
        for card in cards
    )

    category_counts: dict[str, int] = {}

    for card in cards:
        category = str(card.get("category") or "unknown")

        category_counts[category] = (
            category_counts.get(category, 0)
            + int(card["quantity"])
        )

    return {
        "total_cards": total_cards,
        "card_type_rows": len(cards),
        "unique_card_names": len({
            card["card_name"]
            for card in cards
        }),
        "category_counts": category_counts,
        "is_valid_60_cards": total_cards == 60,
    }