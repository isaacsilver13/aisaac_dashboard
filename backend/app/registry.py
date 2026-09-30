from collections.abc import Mapping

from .schemas import AppDefinition

_REGISTRY: Mapping[str, tuple[AppDefinition, ...]] = {
    "local": (
        AppDefinition(
            id="vinyl",
            name="Vinyl Catalog",
            category="Collection",
            description="Record collection and wantlist management.",
            product_url="http://127.0.0.1:8501",
            health_url="http://127.0.0.1:8003/health",
        ),
        AppDefinition(
            id="nfl-confidence",
            name="NFL Confidence",
            category="Sports",
            description="Weekly NFL confidence picks and league standings.",
            product_url="http://127.0.0.1:5173",
            health_url="http://127.0.0.1:8001/api/v1/health",
            readiness_url="http://127.0.0.1:8001/api/v1/health/ready",
        ),
        AppDefinition(
            id="betting-aggregator",
            name="Betting Aggregator",
            category="Sports",
            description="Odds comparison across supported sports and providers.",
            product_url="http://127.0.0.1:5174",
            health_url="http://127.0.0.1:8002/api/v1/health",
            metrics_url="http://127.0.0.1:8002/api/v1/status",
            metric_allowlist=(
                "provider",
                "provider_status",
                "data_stale",
                "event_count",
                "generated_at",
            ),
        ),
        AppDefinition(
            id="nba-prediction",
            name="NBA Prediction",
            category="Research",
            description="NBA prediction experiments, backtests, and model diagnostics.",
            product_url="http://127.0.0.1:8502",
            monitor_target="push",
        ),
        AppDefinition(
            id="gym-tracker",
            name="Gym Tracker",
            category="Health",
            description="Workout routine builder and progress tracker.",
            product_url="http://127.0.0.1:5175",
            health_url="http://127.0.0.1:8004/api/v1/health",
            readiness_url="http://127.0.0.1:8004/api/v1/health/ready",
            metrics_url="http://127.0.0.1:8004/api/v1/health/metrics",
        ),
        AppDefinition(
            id="portfolio-analysis",
            name="Portfolio Analysis",
            category="Finance",
            description="Personal brokerage portfolio import, P&L, and SPY-alpha analysis.",
            product_url="http://127.0.0.1:5176",
            health_url="http://127.0.0.1:8005/api/v1/health",
            readiness_url="http://127.0.0.1:8005/api/v1/health/ready",
        ),
    ),
    "production": (
        AppDefinition(
            id="vinyl",
            name="Vinyl Catalog",
            category="Collection",
            description="Record collection and wantlist management.",
            product_url="https://vinyl-catalog.fly.dev/",
            health_url="https://vinyl-api.fly.dev/health",
            readiness_url="https://vinyl-api.fly.dev/health/ready",
            metrics_url="https://vinyl-api.fly.dev/health/metrics",
        ),
        AppDefinition(
            id="nfl-confidence",
            name="NFL Confidence",
            category="Sports",
            description="Weekly NFL confidence picks and league standings.",
            product_url="https://nfl-confidence-web.fly.dev/",
            health_url="https://nfl-confidence-web.fly.dev/api/v1/health",
            readiness_url="https://nfl-confidence-web.fly.dev/api/v1/health/ready",
        ),
        AppDefinition(
            id="betting-aggregator",
            name="Betting Aggregator",
            category="Sports",
            description="Odds comparison across supported sports and providers.",
            product_url="https://betting-aggregator-api.fly.dev/",
            health_url="https://betting-aggregator-api.fly.dev/api/v1/health",
            metrics_url="https://betting-aggregator-api.fly.dev/api/v1/health/metrics",
            metric_allowlist=(
                "last_activity_at",
                "data_freshness_at",
                "event_count",
                "cache_hit",
                "quota_remaining",
            ),
        ),
        AppDefinition(
            id="nba-prediction",
            name="NBA Prediction",
            category="Research",
            description="NBA prediction experiments, backtests, and model diagnostics.",
            product_url=None,
            monitor_target="push",
        ),
        AppDefinition(
            id="gym-tracker",
            name="Gym Tracker",
            category="Health",
            description="Workout routine builder and progress tracker.",
            product_url="https://isilver-gym-tracker-api.fly.dev/",
            health_url="https://isilver-gym-tracker-api.fly.dev/api/v1/health",
            readiness_url="https://isilver-gym-tracker-api.fly.dev/api/v1/health/ready",
            metrics_url="https://isilver-gym-tracker-api.fly.dev/api/v1/health/metrics",
        ),
        AppDefinition(
            id="portfolio-analysis",
            name="Portfolio Analysis",
            category="Finance",
            description="Personal brokerage portfolio import, P&L, and SPY-alpha analysis.",
            product_url="https://portfolio-analysis-api.fly.dev/",
            health_url="https://portfolio-analysis-api.fly.dev/api/v1/health",
            readiness_url="https://portfolio-analysis-api.fly.dev/api/v1/health/ready",
        ),
    ),
}


def get_registry(profile: str) -> tuple[AppDefinition, ...]:
    try:
        return _REGISTRY[profile]
    except KeyError as error:
        raise ValueError(f"Unknown profile: {profile}") from error
