# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.

---

## Tool Inventory

| Tool Name | Inputs | Outputs | Purpose |
|---|---|---|---|
| `search_listings` | `description` (str), `size` (str \| None), `max_price` (float \| None) | `list[dict]` — up to 3 listing dicts sorted by relevance score. Each dict contains: `id` (str), `title` (str), `description` (str), `category` (str), `style_tags` (list[str]), `size` (str), `condition` (str), `price` (float), `colors` (list[str]), `brand` (str\|None), `platform` (str). Returns `[]` if no match. | Keyword-scores all listings against the description, filters by size (case-insensitive substring match) and max_price, returns top 3 by score. |
| `suggest_outfit` | `new_item` (dict), `wardrobe` (dict), `trend_context` (str, default `""`) | `str` — 1-2 named outfit ideas with piece list and vibe description (≤150 words). If wardrobe is empty, returns general styling advice (≤120 words). Never raises an exception. | Calls the Groq LLM (`llama-3.3-70b-versatile`, `temperature=0.7`, `max_tokens=300`). Uses two separate system prompts depending on whether the wardrobe is empty or populated. If `trend_context` is non-empty, appends it to the user prompt with an explicit instruction to reference at least one trend. |
| `create_fit_card` | `outfit` (str), `new_item` (dict) | `str` — 2-4 sentence Instagram/TikTok-style caption mentioning the item name, price, and platform exactly once each. Returns a descriptive error string (starting with `"Error:"`) if `outfit` is empty or whitespace — does NOT raise an exception. | Guards against empty outfit input, then calls the Groq LLM (`temperature=1.2`, `max_tokens=200`) for a fresh, casual OOTD caption each time. |
| `assess_price` | `new_item` (dict) | `str` — two-part output: (1) a data-driven verdict line showing verdict label, average comparable price, item price, and percentage difference; (2) a one-sentence LLM qualitative assessment. Returns a plain error string if price/condition/category are missing. | Filters `data/listings.json` by same category and overlapping style_tags to compute average price. Then calls the Groq LLM (`temperature=0.3`, `max_tokens=100`) for a qualitative sentence. Combines both into one output string. |
| `get_current_trends` | `category` (str) | `str` — formatted string like `"Current trends for tops: oversized silhouettes, Y2K graphic prints, sheer layering"`, or `""` if the category is not found in `trends.json` or the file is missing/corrupted. | Reads `data/trends.json` (static curated file). Looks up `category.lower()` in the dict. Returns the trend list as a comma-joined string. Handles `FileNotFoundError` and `json.JSONDecodeError` gracefully by returning `""`. |


## Price Comparison

`assess_price` makes comparisons using the following steps:

1. **Filter by category**: All listings in `data/listings.json` that share the same `category` field (e.g. `"tops"`, `"outerwear"`) as the selected item are collected as comparables.
2. **Refine by style_tags**: If the selected item has style tags (e.g. `["vintage", "grunge"]`), comparables are narrowed to listings that share at least one tag — producing a tighter peer group.
3. **Compute average price**: The arithmetic mean of the comparable listings' `price` fields is calculated.
4. **Generate a data-driven verdict**: The item's price is compared to the average. The output always includes: the verdict label (*"On the lower side"* / *"Fairly priced"* / *"On the higher side"*), the average price, the item's price, and the percentage difference — e.g. *"On the lower side for a used item in this category (avg price: $42.00, your price: $24.00, 43% difference)"*.
5. **LLM qualitative assessment**: The item's title, price, category, condition, and description are sent to the Groq LLM (`llama-3.3-70b-versatile`, `temperature=0.3`) for a one-sentence opinion on whether the price is fair for a thrifted item of that type and condition.
6. The final output combines both: the numeric reasoning from step 4 and the LLM's sentence from step 5.

## Trend Awareness

FitFindr uses current fashion trends to make its outfit suggestions more relevant and modern.

**Data source:** A curated, static dataset located at `data/trends.json`. This file contains 3-5 current fashion trends for each major clothing category (e.g., tops, bottoms, outerwear), populated based on 2025 season fashion reporting. It is updated manually each season.

**How it influences the output:**
1. During the planning loop, the agent looks up the category of the selected thrifted item in the `data/trends.json` file.
2. If trends are found for that category, they are formatted into a context string (e.g., *"Current trends for tops: oversized silhouettes, Y2K graphic prints..."*).
3. This context string is injected directly into the system prompt for the `suggest_outfit` tool.
4. The LLM is explicitly instructed: *"You MUST reference at least one of these trends naturally in your outfit suggestion."*
5. As a result, the generated outfit idea visibly incorporates real-world trend data rather than just generic styling advice.

**Graceful fallback:** If an item belongs to a category not listed in `trends.json`, the tool simply returns an empty string, and `suggest_outfit` runs normally without the trend constraint, preventing any crashes.

## Planning Loop Explanation

1. The user query and selected wardrobe enter the loop via `run_agent()`.
2. **Parse Query** — `_get_groq_client()` (LLM): The user types natural language like *"vintage graphic tee under $30 in size M"*. The agent calls the LLM first because `search_listings` requires structured parameters (`description`, `size`, `max_price`), not a raw sentence. The LLM extracts those fields and returns a JSON object stored in `session["parsed"]`.
3. **Search** — `search_listings()`: Called with the parsed parameters. After it runs, the loop checks `if not results`. **If True (empty list):** the loop sets `session["error"]` to `"We couldn't find any items matching your exact description, size, and price. Try broadening your search terms, removing the size filter, or increasing your budget!"` and immediately returns the session — `suggest_outfit` and `create_fit_card` are never called. **If False (results found):** `session["search_results"]` is populated and execution continues to Step 4.
4. **Select**: The top-scored item (`results[0]`) is stored in `session["selected_item"]` so downstream tools can access it without re-running the search.
5. **Suggest Outfit** — `suggest_outfit()`: Only reached if Step 3 returned results. Called with `session["selected_item"]` and the wardrobe. The result (1-2 complete outfit ideas) is stored in `session["outfit_suggestion"]`.
6. **Create Fit Card** — `create_fit_card()`: Only reached after a successful outfit suggestion. Called with `session["outfit_suggestion"]` and `session["selected_item"]` to generate a caption mentioning the item name, price, platform, and outfit vibe. The result is stored in `session["fit_card"]`.
7. The loop returns the `session` dictionary. The Gradio UI (`app.py`) maps the three output fields to the three display panels.

## State Management Approach

The agent uses a centralized `session` dictionary as the single source of truth for one user interaction, initialized by `_new_session()` at the start of `run_agent()`. Here is exactly what is stored, when, and how it flows between tools:

| When | Key Written | Value | Passed Into Next Tool As |
|---|---|---|---|
| After LLM parse | `session["parsed"]` | `{"description": str, "size": str\|None, "max_price": float\|None}` | Keyword arguments to `search_listings()` |
| After search | `session["search_results"]` | List of up to 3 listing dicts | (not passed further; used for early-exit check) |
| After select | `session["selected_item"]` | The top listing dict from search results | First argument (`new_item`) to `suggest_outfit()` and `create_fit_card()` |
| After suggest | `session["outfit_suggestion"]` | Outfit suggestion string from the LLM | First argument (`outfit`) to `create_fit_card()` |
| After fit card | `session["fit_card"]` | Social-media caption string from the LLM | Returned to the UI via `app.py` |
| On any error | `session["error"]` | Descriptive error string | Returned to the UI and triggers early exit before remaining tools are called |

No tool reads from the session dict directly — each tool receives its inputs as explicit function arguments extracted from the session by the planning loop. The user never re-enters any value between steps.

## Error Handling per Tool

- **`search_listings`**: Handles impossible queries (e.g., max_price too low, wrong size) by returning an empty list `[]` instead of raising an exception. 
  - *Concrete Example:* Querying `"designer ballgown"` with `size="XXS"` and `max_price=5` returned `[]`. The agent loop gracefully handled this by setting `session["error"]` to a helpful message and terminating early.
- **`suggest_outfit`**: Handles an empty wardrobe gracefully by checking `if not wardrobe.get("items")`. Instead of crashing, it prompts the LLM for general styling advice. 
  - *Concrete Example:* Providing a new "Vintage Leather Jacket" with an empty wardrobe resulted in the LLM giving general tips like *"Pair this with high-waisted jeans..."* instead of hallucinating wardrobe pieces.
- **`create_fit_card`**: Guards against empty or whitespace-only outfit strings before calling the LLM.
  - *Concrete Example:* Calling `create_fit_card("   ", item)` immediately returned `"Error: No outfit suggestion was provided, so a fit card could not be generated. Try searching for an item first and making sure the outfit suggestion step completes successfully."` — no LLM call is made and the user is told exactly what to fix.

## Spec Reflection

**How the spec helped:** Defining the exact inputs, outputs, and fallback behaviors for each tool upfront in `planning.md` made the implementation process remarkably smooth. Because the return value of `search_listings` was fully specified (a list of dicts with named fields), `suggest_outfit` could be written and tested in isolation long before the planning loop connected them — no surprises at integration time. This approach directly supported the modular development recommended by the prompt.

**One divergence and why:** The original spec for `suggest_outfit` said *"if it can't suggest an outfit for any other reason, it should return an empty string and the agent should try again."* In the actual implementation, there is no retry logic. Instead, the LLM is called once and its response is returned directly. The spec's "try again" instruction was dropped because: (1) LLM failures for `suggest_outfit` are extremely rare in practice — if the wardrobe is valid and the item dict is non-empty, the model reliably returns something; and (2) adding a retry loop would complicate the planning loop significantly for a case that almost never happens. The empty-wardrobe case (which was the primary failure mode) is handled correctly by falling back to general styling advice.

## AI Usage Section

### Instance 1: JSON Parsing Fix in Agent Loop
- **Input**: The `agent.py` code where `json.loads(parsed_query)` was crashing with a `JSONDecodeError`, along with the terminal stack trace.
- **Output**: The AI recognized that the LLM was wrapping its JSON output in markdown backticks. It provided an updated `model.chat.completions.create` call including `response_format={"type": "json_object"}`, `temperature=0.0`, and a stricter system prompt.
- **Change/Override**: I integrated the `response_format` and `temperature` adjustments into the agent loop. I also modified the system prompt slightly to ensure missing values like `size` or `max_price` were explicitly set to `null` to match the Python `None` types expected by `search_listings`.

### Instance 2: LLM Prompt Tuning for Outfit Suggestions
- **Input**: The `tools.py` code for `suggest_outfit` and a complaint that the LLM output was a giant wall of text with unwanted "Styling Tips" and "Wardrobe Building" sections.
- **Output**: The AI suggested rewritten system and user prompts with explicit negative constraints ("Do NOT include styling tips sections...") and strict format rules ("Name each outfit, list the pieces, and describe the vibe in 1 sentence"), plus lowering `max_tokens` to 300.
- **Change/Override**: The AI's initial suggestion included a single system prompt with a 200-word limit. I overrode this with two separate system prompts — one for the empty-wardrobe branch (120-word cap) and one for the populated-wardrobe branch (150-word cap) — because a single limit failed to account for the fact that the empty-wardrobe path has fewer pieces to name and should be shorter. I also kept `temperature=0.7` rather than accepting the AI's suggestion of `temperature=1.0`, since higher temperature caused the outfit names to be inconsistently formatted. Verified through pytest tests 6 and 7 that the output stayed within 2 outfits in both branches.
