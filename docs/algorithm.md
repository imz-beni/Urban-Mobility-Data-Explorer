# Custom Algorithm — Ranking the Busiest Pickup Zones

**Author:** Derrick · **Lives in:** `backend/app.py` (`rank_busiest`), served at `/api/busiest-zones`

## The problem it solves
The dashboard needs the top pickup zones by trip volume — a real "how does the city
move?" question. Rather than lean on SQL `ORDER BY` or Python helpers, the rubric
requires a **hand-built** algorithm with **no built-in libraries** (no `Counter`, no
`.sort()`, no `heapq`). So this is done in two manual passes: count, then sort.

## Plain-English explanation
1. **Count by hand** — walk every trip row once, keeping a running tally per pickup
   zone in a plain dictionary (`counts[z] = counts.get(z, 0) + 1`). No `Counter`.
2. **Selection sort, descending** — repeatedly scan the unsorted remainder for the
   zone with the largest count and swap it into place, so the highest-volume zones end
   up first. No `.sort()`.
3. Return the **top 10** as `{zone, trips}` pairs for the chart.

## Pseudo-code
```
function rank_busiest(rows):
    counts = empty map
    for each row in rows:
        z = row.pu_zone_id
        counts[z] = counts[z] + 1        # default 0 if unseen

    items = list of (zone, count) pairs from counts
    n = length(items)

    for i from 0 to n-1:                  # selection sort, descending
        biggest = i
        for j from i+1 to n-1:
            if items[j].count > items[biggest].count:
                biggest = j
        swap items[i] and items[biggest]

    return first 10 of items as {zone, trips}
```

## Complexity analysis
- **Time:** `O(n + k^2)`
  - Counting pass is `O(n)` over `n` trips.
  - Selection sort is `O(k^2)` where `k` = number of distinct zones.
- **Space:** `O(k)` for the counts map (plus the `items` list, also `O(k)`).

Here `n` is large (every trip) but `k` is small and bounded — NYC has only ~260 taxi
zones — so `k^2` is tiny and constant in practice. The cost is dominated by the linear
counting pass.

## Why selection sort (the design choice to defend)
Because `k` is small and fixed (~260), a simple quadratic sort is more than fast enough,
and it's trivial to explain line-by-line in a random call-out. A fancier `O(k log k)`
sort would add complexity for no measurable gain at this scale. Choosing the simplest
algorithm that's obviously correct *is* the justification.
