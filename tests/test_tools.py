from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


################################ Tests for search_listings tool ################################

# Test 1: Query that should return results
print("=== Test 1: vintage graphic tee, size M, max $30 ===")
results = search_listings("vintage graphic tee", "M", 30.0)
assert(len(results) == 3)
print("[PASS]: search_listings returns results for vintage graphic tee")

# Test 2: Size filter that eliminates all matches
print("=== Test 2: vintage graphic tee, size XXS (no match expected) ===")
results2 = search_listings("vintage graphic tee", "XXS", 30.0)
assert(len(results2) == 0)
print("[PASS]: Size filter works")

# Test 3: Price filter that cuts everything out
print("=== Test 3: vintage jacket, no size, max $1.00 (no match expected) ===")
results3 = search_listings("vintage jacket", None, 1.0)
assert(len(results3) == 0)
print("[PASS]: Price filter works")

# Test 4: Broad query — no size/price filter
print("=== Test 4: baggy jeans, no filters ===")
results4 = search_listings("baggy jeans")
assert(len(results4) > 0)
print("[PASS]: search_listings returns results for broad queries")


################################# Tests for suggest_outfit tool ###################################

print('\n=== Test 5: suggest_outfit with Empty Wardrobe ===')
new_item = {
    'title': 'Vintage Leather Jacket',
    'description': 'Classic black leather moto jacket.',
    'category': 'outerwear'
}
empty_wardrobe = get_empty_wardrobe()
suggestion_empty = suggest_outfit(new_item, empty_wardrobe)
print(suggestion_empty)

print('\n=== Test 6: suggest_outfit with Populated Wardrobe ===')
populated_wardrobe = get_example_wardrobe()
suggestion_populated = suggest_outfit(new_item, populated_wardrobe)
print(suggestion_populated)


################################# Tests for create_fit_card tool ###################################

# Shared inputs for Tests 7–9
fit_card_item = {
    "title": "Vintage Levi's 501 Jeans — Medium Wash",
    "price": 38.0,
    "platform": "depop",
}
fit_card_outfit = (
    "Outfit: Pair the Levi's 501s with a white ribbed tank top and chunky white sneakers. "
    "Layer a cropped black zip hoodie over the top for a relaxed streetwear vibe."
)

# Test 7: Guard — empty outfit string must return an error message, not crash
print('\n=== Test 7: create_fit_card — empty outfit (error guard) ===')
result_empty = create_fit_card("", fit_card_item)
print(f"  -> '{result_empty}'")
assert result_empty.startswith("Error:"), f"Expected error message, got: {result_empty}"
print("  [PASS] Guard works correctly\n")

# Test 8: create_fit_card — whitespace-only outfit also triggers the guard
print('=== Test 8: create_fit_card — whitespace-only outfit (error guard) ===')
result_ws = create_fit_card("   ", fit_card_item)
print(f"  -> '{result_ws}'")
assert result_ws.startswith("Error:"), f"Expected error message, got: {result_ws}"
print("  [PASS] Guard works correctly\n")

# Test 9: create_fit_card — real caption, called 3× to verify output variety
print('=== Test 9: create_fit_card — 3 calls on the same input (verify variety) ===')
captions = [create_fit_card(fit_card_outfit, fit_card_item) for _ in range(3)]
for idx, cap in enumerate(captions, 1):
    print(f"  [{idx}] {cap}\n")
unique_count = len(set(captions))
print(f"  -> {unique_count}/3 unique captions (expected > 1)")
assert unique_count > 1, "All 3 captions are identical — increase LLM temperature!"
print("  [PASS] Output varies across calls")
