"""Analytics API — backward-compatibility shim.

All endpoints have been moved to domain-specific modules:
  - analytics_metrics.py  : /analytics/metrics, /analytics/monthly-returns, /analytics/sector-allocation
  - analytics_history.py  : /analytics/portfolio-history, /analytics/krw-asset-history
  - analytics_fx.py       : /analytics/fx-gain-loss, /analytics/fx-history

This module re-exports invalidate_analytics_cache for callers that import from app.api.analytics.
Do not add new endpoints here; add them to the appropriate split module instead.
"""

from app.services.analytics_utils import (
    invalidate_analytics_cache,  # noqa: F401 — re-exported for backward compatibility
)

__all__ = ["invalidate_analytics_cache"]
