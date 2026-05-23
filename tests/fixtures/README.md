# Agent Testing Fixtures

Curated sample data for **Try-On Visualization** and **Guardrail** agent development.

## Files

| File | Purpose |
|------|---------|
| `sample_catalog.json` | 16 catalog items picked from `data/gymshark_closet_inventory.json` |
| `sample_recommendations.json` | 6 pre-built outfit recommendations referencing catalog item IDs |

## Selection criteria

Items were chosen from the full Gymshark closet inventory to cover:

- **Men's and women's** product shots
- **Categories:** top, bottom, outerwear, sports bra
- **Visual variety:** solid black, marl knit, fleck/mineral patterns, seamless texture
- **Try-on geometry:** tee, tank, long sleeve, shorts, joggers, leggings, hoodie
- **Excluded:** accessories (backpack, socks, bottles), one-pieces (harder try-on for v1)

## Quick lookup by test scenario

| Scenario | Recommendation ID | Items |
|----------|-------------------|-------|
| Baseline men's try-on | `rec_m_gym_001` | Crest tee + Arrival shorts |
| Multi-garment men's | `rec_m_street_002` | Long sleeve + joggers + hoodie |
| Pattern fidelity (men) | `rec_m_pattern_003` | Geo seamless tee + shorts |
| Baseline women's try-on | `rec_w_vital_001` | Vital crop + Vital leggings |
| Color/pattern stress test | `rec_w_adapt_002` | Adapt fleck top + leggings |
| Complex garment types | `rec_w_layered_003` | Sports bra + leggings + zip pullover |

## Customer photos

Test photos for try-on agent development (stock placeholders):

```
customers/
  customer_01_fullbody.jpeg   # default for test script
  customer_02_upperbody.jpeg  # partial framing edge case
```

Replace with real full-body customer photos for better try-on quality during demo prep.

## Guardrail labels (you provide)

After generating try-ons, label outputs in `guardrail_labels.json` (not yet created).

## Source data

Full inventory: `data/gymshark_closet_inventory.json` (52 items, mens + womens)  
Full product catalog: `data/gymshark_products.json` (8000+ items)

## Generated outputs

The test script writes try-on PNGs and guardrail JSON to `tests/fixtures/outputs/` (gitignored).
