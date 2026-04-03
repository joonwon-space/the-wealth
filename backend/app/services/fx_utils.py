"""FX rate utility functions shared across analytics and scheduler modules."""

from collections.abc import Sequence


def forward_fill_rates(
    snapshots: Sequence[object],
    dates: list[str],
    fallback_rate: float,
) -> dict[str, float]:
    """Build a date → rate mapping by forward-filling gaps from snapshot data.

    Args:
        snapshots: Sequence of objects with ``snapshot_date`` (date) and
            ``rate`` (Decimal|float) attributes, ordered by snapshot_date.
        dates: Sorted list of ISO date strings to fill (e.g. ``["2025-01-01", ...]``).
        fallback_rate: Rate to use before the first known snapshot.

    Returns:
        Dict mapping each date in ``dates`` to the most-recently-known rate
        (forward-filled).  The fallback is used for any date prior to the
        earliest snapshot.
    """
    fx_date_map: dict[str, float] = {
        snap.snapshot_date.isoformat(): float(snap.rate)  # type: ignore[attr-defined]
        for snap in snapshots
    }

    filled: dict[str, float] = {}
    last_known: float = fallback_rate
    for d in dates:
        if d in fx_date_map:
            last_known = fx_date_map[d]
        filled[d] = last_known
    return filled
