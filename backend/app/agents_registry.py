from .schemas import AgentDefinition

_AGENTS: tuple[AgentDefinition, ...] = (
    AgentDefinition(
        id="repo-maintainer",
        name="Repo Manager",
        domain="Repo hygiene",
        description="Audits READMEs, repo metadata, and commit/code hygiene across every repo.",
        scope=(
            "vinyl",
            "nfl-confidence",
            "betting-aggregator",
            "nba-prediction",
            "gym-tracker",
            "portfolio-analysis",
        ),
    ),
    AgentDefinition(
        id="sports-data",
        name="Sports & Data",
        domain="Sports & data",
        description="Owns NFL Confidence, NBA Prediction, and the Betting Aggregator.",
        scope=("nfl-confidence", "nba-prediction", "betting-aggregator"),
    ),
    AgentDefinition(
        id="app-ops",
        name="App Ops",
        domain="App operations",
        description="Keeps Vinyl, Gym Tracker, and Portfolio Analysis healthy and moving.",
        scope=("vinyl", "gym-tracker", "portfolio-analysis"),
    ),
    AgentDefinition(
        id="career",
        name="Career",
        domain="Job search",
        description="Tracks the job search: applications, resume audits, and outreach follow-ups.",
        scope=(),
    ),
)


def get_agents() -> tuple[AgentDefinition, ...]:
    return _AGENTS
