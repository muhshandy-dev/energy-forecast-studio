"""Padanan Python untuk transformasi skenario di browser (web/src/lib/scenario.ts).

Dipakai untuk membuat vektor uji bersama agar kedua implementasi terbukti sama.
"""

from __future__ import annotations

import numpy as np


def scale_factor(shift_pct: float) -> float:
    if not np.isfinite(shift_pct) or shift_pct <= -100:
        raise ValueError("geser level harus > -100%")
    return 1 + shift_pct / 100


def exceedance(probs, quantiles, capacity: float) -> tuple[float, str]:
    """(peluang beban > capacity, jenis: exact | atLeast | atMost)."""
    probs = np.asarray(probs, dtype=float)
    q = np.asarray(quantiles, dtype=float)
    if capacity < q[0]:
        return float(1 - probs[0]), "atLeast"
    if capacity >= q[-1]:
        return float(1 - probs[-1]), "atMost"
    i = int(np.searchsorted(q, capacity, side="right") - 1)
    q0, q1 = q[i], q[i + 1]
    if q1 == q0:
        cdf = probs[i + 1]
    else:
        cdf = probs[i] + (capacity - q0) / (q1 - q0) * (probs[i + 1] - probs[i])
    return float(1 - cdf), "exact"
