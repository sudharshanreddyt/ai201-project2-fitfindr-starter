"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    # 1. Load all listings from the dataset
    listings = load_listings()

    # 2. Filter by max_price and size (if provided)
    filtered = []
    for item in listings:
        # Price filter: drop items that exceed max_price
        if max_price is not None and item["price"] > max_price:
            continue

        # Size filter: case-insensitive substring match
        # e.g. "M" matches "S/M", "M/L", "M", etc.
        if size is not None and size.strip():
            if size.lower() not in item["size"].lower():
                continue
        filtered.append(item)

    # 3. Score each remaining listing by keyword overlap with `description`

    # Build a set of lowercase tokens from the query
    query_tokens = set(description.lower().split())

    scored = []
    for item in filtered:
        score = 0

        # Score against title tokens
        title_tokens = set(item["title"].lower().split())
        score += len(query_tokens & title_tokens)

        # Score against description tokens
        desc_tokens = set(item["description"].lower().split())
        score += len(query_tokens & desc_tokens)

        # Score against style_tags (each tag is already a short phrase)
        for tag in item.get("style_tags", []):
            tag_tokens = set(tag.lower().split())
            if query_tokens & tag_tokens:
                score += 1

        scored.append((score, item))

    # 4. Drop any listings with a score of 0 (no relevant keyword matches)
    scored = [(s, item) for s, item in scored if s > 0]

    # 5. Sort by score highest first and return the listing dicts (up to 3)
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:3]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    # 1. Check whether wardrobe['items'] is empty.
    items = wardrobe.get("items", [])
    
    # Format the new item for the prompt
    title = new_item.get("title", "Unknown Item")
    desc = new_item.get("description", "")
    new_item_str = f"'{title}' - {desc}"
    
    if not items:
        # 2. If empty: prompt for general styling ideas
        system_prompt = (
            "You are a concise fashion stylist. Give only 1-2 complete outfit ideas. "
            "Do NOT include styling tips sections, wardrobe-building advice, or closing questions. "
            "Keep your response under 120 words."
        )
        user_prompt = (
            f"I thrifted: {new_item_str}. My wardrobe is empty.\n"
            "Suggest 1-2 outfit ideas using types of pieces that pair well with it. "
            "Name each outfit, list the pieces, and describe the vibe in 1 sentence. Nothing else."
        )
    else:
        # 3. If not empty: ask for specific outfit combinations
        system_prompt = (
            "You are a concise fashion stylist. Give only 1-2 complete outfit combinations. "
            "Do NOT include styling tips, wardrobe-building advice, or closing questions. "
            "Keep your response under 150 words."
        )
        wardrobe_list = []
        for i in items:
            tags = ", ".join(i.get("style_tags", []))
            notes = i.get("notes") or ""
            notes_str = f" | Notes: {notes}" if notes else ""
            wardrobe_list.append(f"- {i.get('name', 'Unknown')} ({i.get('category', '')}){' | Tags: ' + tags if tags else ''}{notes_str}")
        wardrobe_str = "\n".join(wardrobe_list)
        
        user_prompt = (
            f"I thrifted: {new_item_str}.\n"
            f"My wardrobe:\n{wardrobe_str}\n\n"
            "Suggest exactly 1-2 complete outfits using my new item and named wardrobe pieces. "
            "For each outfit: give it a name, list the pieces by name, describe the vibe in 1 sentence. "
            "Do NOT add styling tips, extra advice, or a closing question."
        )

    # Call the Groq LLM
    client = _get_groq_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=300
    )
    
    # 4. Return the LLM's response as a string.
    return response.choices[0].message.content.strip()


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    # 1. Guard against an empty or whitespace-only outfit string.
    if not outfit or not outfit.strip():
        return "Error: No outfit suggestion available to generate a fit card."

    # Extract item details for the prompt
    title    = new_item.get("title", "Unknown Item")
    price    = new_item.get("price", "?")
    platform = new_item.get("platform", "a thrift platform")

    # 2. Build the prompt with all required style guidelines.
    system_prompt = (
        "You are a fashion-forward social media writer who creates short, punchy outfit captions "
        "for Instagram and TikTok. Write like a real person posting their OOTD — casual, specific, "
        "and enthusiastic. Never sound like a product listing."
    )
    user_prompt = (
        f"I thrifted '{title}' for ${price} on {platform}.\n"
        f"Here's the outfit I'm building with it:\n{outfit}\n\n"
        "Write a 2-4 sentence Instagram/TikTok caption for this outfit. Rules:\n"
        "- Sound casual and authentic, like a real OOTD post\n"
        "- Mention the item name, price, and platform exactly once each, woven in naturally\n"
        "- Capture the specific vibe of this outfit (don't use generic phrases like 'great look')\n"
        "- Each caption should feel fresh and different — avoid formulaic openers"
    )

    # 3. Call the LLM with high temperature so outputs vary across repeated calls.
    client = _get_groq_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=1.2,
        max_tokens=200,
    )

    return response.choices[0].message.content.strip()
