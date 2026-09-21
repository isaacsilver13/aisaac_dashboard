from .schemas import RepoDefinition

_REPOS: tuple[RepoDefinition, ...] = (
    RepoDefinition(
        id="vinyl",
        name="Vinyl Catalog",
        category="Collection",
        owner="isaacsilver13",
        repo="vinyl",
    ),
    RepoDefinition(
        id="nfl-confidence",
        name="NFL Confidence",
        category="Sports",
        owner="isaacsilver13",
        repo="NFL_Confidence",
    ),
    RepoDefinition(
        id="betting-aggregator",
        name="Betting Aggregator",
        category="Sports",
        owner="isaacsilver13",
        repo="betting_aggregator",
    ),
    RepoDefinition(
        id="nba-prediction",
        name="NBA Prediction",
        category="Research",
        owner="isaacsilver13",
        repo="nba_prediction",
    ),
    RepoDefinition(
        id="gym-tracker",
        name="Gym Tracker",
        category="Health",
        owner="isaacsilver13",
        repo="gym_tracker",
    ),
    RepoDefinition(
        id="portfolio-analysis",
        name="Portfolio Analysis",
        category="Finance",
        owner="isaacsilver13",
        repo="portfolio_analysis",
    ),
)


def get_repos() -> tuple[RepoDefinition, ...]:
    return _REPOS
