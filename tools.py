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

import json
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

def suggest_outfit(new_item: dict, wardrobe: dict, trend_context: str = "") -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.
        trend_context: A string containing current trends for the category, 
                       as returned by get_current_trends()

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

    if trend_context:
        user_prompt += f"\n The following trends are currently popular for this category: {trend_context}.\n\n You MUST reference at least one of these trends naturally in your outfit suggestion."
    
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
        return "Error: No outfit suggestion was provided, so a fit card could not be generated. Try searching for an item first and making sure the outfit suggestion step completes successfully."

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


# ── Tool 4: assess_price ───────────────────────────────────────────────────

def assess_price(new_item: dict) -> str:
    """
    Assess whether the price of a thrifted item is fair/average/high
    based on its category, condition, and description.

    Args:
        new_item: A listing dict (the item the user is considering buying).

    Returns:
        A string giving a quick price assessment (e.g. "Fairly priced for a used item in this category",
        "On the higher side, but consistent with brand value", or "A really good deal for this condition").

    TODO:
        1. Extract the item's category, condition, and price.
        2. Load all listings using load_listings() from utils/data_loader.py
        3. Filter to listings in the same category as the item (e.g., "tops", "outerwear")
        4. Optionally also filter by overlapping style_tags for tighter comparisons
        5. Calculate the average price of those comparable listings
        6. Compare the item's price to that average and generate a verdict string with the numbers
        7. Build a prompt that asks the LLM to compare this item's price to a typical
           thrifted item in the same category and condition.
        8. Call the LLM and return its assessment as a short string.

    Before writing code, fill in the Tool 4 section of planning.md.
    """
    
    # 1. Extract the item's category, condition, and price.
    title    = new_item.get("title", "Unknown Item")
    desc     = new_item.get("description", "")
    category = new_item.get("category", "Unknown Category")
    price    = new_item.get("price", "?")
    condition = new_item.get("condition", "Unknown Condition")
    style_tags = new_item.get("style_tags", [])

    # Guard against empty/missing values for assessment
    if not price or not condition or not category:
        return "Unable to assess price: Missing item details (price, condition, and category are all unknown)."

    # 2. Load all listings using load_listings() from utils/data_loader.py
    listings = load_listings()

    # 3. Filter to listings in the same category as the item (e.g., "tops", "outerwear")
    category_listings = [l for l in listings if l.get("category") == category]

    # 4. Optionally also filter by overlapping style_tags for tighter comparisons
    if style_tags:
        category_listings = [l for l in category_listings if any(tag in style_tags for tag in l.get("style_tags", []))]

    # 5. Calculate the average price of those comparable listings
    if not category_listings:
        return "No comparable listings found to assess price."

    category_prices = [l.get("price", 0) for l in category_listings]
    avg_price = sum(category_prices) / len(category_prices) if category_prices else 0

    # 6. Compare the item's price to that average and generate a verdict string with the numbers
    if avg_price == 0:
        verdict = "Fairly priced"
    elif price < avg_price:
        verdict = "On the lower side"
    elif price > avg_price:
        verdict = "On the higher side"
    else:
        verdict = "Fairly priced"

    price_difference = abs(price - avg_price)
    percentage_difference = 0
    if avg_price > 0:
        percentage_difference = (price_difference / avg_price) * 100
        verdict_string = f"{verdict} for a used item in this category (avg price: ${avg_price:.2f}, your price: ${price:.2f}, {percentage_difference:.0f}% difference)"
    else:
        verdict_string = f"{verdict} for a used item in this category"

    # 7. Build a prompt that asks the LLM to compare this item's price to a typical thrifted item in the same category and condition.
    system_prompt = (
        "You are a thrift shopping expert who knows what items typically cost secondhand. Give concise, honest price assessments."
    )

    user_prompt = (
        f"I found '{title}' for ${price}." 
        f"\nCategory: {category}"
        f"\nCondition: {condition}"
        f"\nDescription: {desc}"
        "\nAssess in one sentence whether this price is fair, high, or low for a thrifted item in this category and condition."
    )

    # 3. Call the LLM and return its assessment as a short string.
    client = _get_groq_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=100,
    )

    llm_assessment = response.choices[0].message.content.strip()
    return f"{verdict_string}\n{llm_assessment}" # LLM assessment + data-driven assessment


# ── Tool 5: get_current_trends ───────────────────────────────────────────────────

def get_current_trends(category: str) -> str:
    """
    Returns a human-readable summary of current trending thrift flips for the given category.

    Args:
        category: The category of items to get trends for (e.g., "tops", "bottoms").

    Returns:
        A string with current trends for the category, or an empty string if not found.

    TODO:
        1. Import json and os at the top.
        2. Open data/trends.json — use os.path.join(os.path.dirname(__file__), "data", "trends.json") to build the path.
        3. Look up the category key in the loaded dict.
        4. If the category exists, return a formatted string like "Current trends for this category: oversized silhouettes, Y2K graphic prints, sheer layering."
        5. If the category doesn't exist, return an empty string "" — so the rest of the pipeline doesn't crash.
    """
    # Get the path to the trends.json file, which should be in the same directory as this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    trends_path = os.path.join(script_dir, "data", "trends.json")

    # 2. Load the trends data from the JSON file
    try:
        with open(trends_path, "r") as f:
            trends = json.load(f)
    except FileNotFoundError:
        return "" # Return an empty string if the file isn't found
    except json.JSONDecodeError:
        return "" # Return an empty string if the file is corrupted
    
    # 3. Look up the category key in the loaded dict.
    category_trends = trends.get(category.lower(), [])
    
    # 4. If the category exists, return a formatted string like "Current trends for this category: oversized silhouettes, Y2K graphic prints, sheer layering."
    if category_trends:
        return f"Current trends for {category}: {', '.join(category_trends)}"

    # 5. If the category doesn't exist, return an empty string "" — so the rest of the pipeline doesn't crash.
    return ""
