"""Small, dependency-free statistics helpers for the dashboard."""
from math import comb, sqrt

def wilson(k, n, z=1.96):
    """95% Wilson score interval for a proportion, as (low, high) in [0,1]. Returns (0,0) for n=0."""
    if n == 0: return 0.0, 0.0
    p = k / n; denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)

def fisher_two_sided(a, b, c, d):
    """Two-sided Fisher exact p-value for the 2x2 table [[a, b], [c, d]] (rows = groups, cols = yes/no)."""
    n = a + b + c + d; r1 = a + b; c1 = a + c
    if n == 0 or r1 == 0 or c1 == 0 or r1 == n or c1 == n: return 1.0
    total = comb(n, c1)
    prob = lambda x: comb(r1, x) * comb(n - r1, c1 - x) / total
    p_obs = prob(a)
    lo, hi = max(0, c1 - (n - r1)), min(r1, c1)
    return min(1.0, sum(prob(x) for x in range(lo, hi + 1) if prob(x) <= p_obs * (1 + 1e-9)))

def rate(k, n):
    """Dict with count, n, proportion and Wilson CI, ready for display."""
    lo, hi = wilson(k, n)
    return dict(k=k, n=n, p=(k / n if n else None), lo=lo, hi=hi)
