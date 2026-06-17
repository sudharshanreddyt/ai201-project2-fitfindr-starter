"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

from tools import search_listings, suggest_outfit, create_fit_card, assess_price, get_current_trends, _get_groq_client
import json

# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "price_verdict": None,       # string returned by assess_price
        "trend_context": None,       # string returned by get_current_trends
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

    TODO — implement this function using the planning loop you designed in planning.md:

        Step 1: Initialize the session with _new_session().

        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4a: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].
        Step 4b: Get current trends for the selected item's category
                Store the result in session["trend_context"]. If no trends are found, set session["trend_context"] to None (optional).
        
        Step 5: Call suggest_outfit() with the selected item and wardrobe.
                Store the result in session["outfit_suggestion"].

        Step 6: Call create_fit_card() with the outfit suggestion and selected item.
                Store the result in session["fit_card"].

        Step 7: Return the session.

    Before writing code, complete the Planning Loop and State Management sections
    of planning.md — your implementation should match what you described there.
    """
    # TODO: implement the planning loop

    # Step 1: Initialize the session with _new_session().
    session = _new_session(query, wardrobe)

    # Step 2: Parse the user's query to extract a description, size, and max_price.
    # Use LLM for parsing the query and store it in session["parsed"].
    model = _get_groq_client()
    response_dict = model.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system", 
                "content": "You are an expert parsing assistant. Parse the following user's query to extract a description, size, and max_price. You must return ONLY a valid JSON object with keys 'description', 'size', and 'max_price'. If a value is not found, set it to null."
            },
            {
                "role": "user", 
                "content": session["query"]
            }
        ],
        response_format={ "type": "json_object" },
        temperature=0,
    )
    parsed_query = response_dict.choices[0].message.content
    parsed_query = json.loads(parsed_query) # convert the parsed query from a string to a dictionary
    session["parsed"] = parsed_query
    
    
    # Step 3: Call search_listings() with the parsed parameters.
    # Store results in session["search_results"].
    # If no results: set session["error"] to a helpful message and return the session early.
    # Do NOT proceed to suggest_outfit with empty input.
    
    results = search_listings(
        description=parsed_query["description"],
        size=parsed_query["size"],
        max_price=parsed_query["max_price"],
    )
    
    session["search_results"] = results # always store, even if []
    
    if not results: # if the results list is empty
        session["error"] = "We couldn't find any items matching your exact description, size, and price. Try broadening your search terms, removing the size filter, or increasing your budget!"
        return session

    # Step 4a: Select the item to use (e.g., the top result).
    # Store it in session["selected_item"].
    session["selected_item"] = results[0]

    # Step 4b: Get current trends for the selected item's category
    # Store the result in session["trend_context"]. If no trends are found, set session["trend_context"] to None (optional).
    category = session["selected_item"]["category"]
    if category:
        trends = get_current_trends(category)
        session["trend_context"] = trends
    else:
        session["trend_context"] = None
    
    # Step 5: Call suggest_outfit() with the selected item and wardrobe.
    # Store the result in session["outfit_suggestion"].
    suggested_outfit = suggest_outfit(
        session["selected_item"],
        wardrobe,
        trend_context=session["trend_context"]
    )
    session["outfit_suggestion"] = suggested_outfit
    
    # Step 6: Call create_fit_card() with the outfit suggestion and selected item.
    # Store the result in session["fit_card"].
    fit_card = create_fit_card(
        suggested_outfit,
        session["selected_item"],
    )
    session["fit_card"] = fit_card

    # Step 7: Assess the price of the selected item
    price_verdict = assess_price(session["selected_item"])
    session["price_verdict"] = price_verdict

    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
