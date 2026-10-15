"""
analytics/domains — Domain-specific analytics modules.
"""

from analytics.domains.commerce import compute_commerce_analytics
from analytics.domains.feedback import compute_feedback_analytics
from analytics.domains.finance import compute_finance_analytics
from analytics.domains.workforce import compute_workforce_analytics
from analytics.profiler import (
    DOMAIN_COMMERCE,
    DOMAIN_FEEDBACK,
    DOMAIN_FINANCE,
    DOMAIN_WORKFORCE,
)

__all__ = [
    "DOMAIN_COMMERCE",
    "DOMAIN_FEEDBACK",
    "DOMAIN_FINANCE",
    "DOMAIN_WORKFORCE",
    "compute_commerce_analytics",
    "compute_feedback_analytics",
    "compute_finance_analytics",
    "compute_workforce_analytics",
]
