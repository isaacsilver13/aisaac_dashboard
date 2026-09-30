from urllib.parse import urlparse

from app.registry import get_registry

# These apps now ship as one Fly app serving both UI and API, so the old
# split -web/-api hostnames no longer exist.
RETIRED_HOSTS = {
    "nfl-confidence-api.fly.dev",
    "betting-aggregator-web.fly.dev",
    "isilver-gym-tracker-web.fly.dev",
    "portfolio-analysis-web.fly.dev",
}
SINGLE_HOST_APPS = {"nfl-confidence", "betting-aggregator", "gym-tracker", "portfolio-analysis"}


def _hosts(app) -> dict[str, str]:
    urls = {
        "product": app.product_url,
        "health": app.health_url,
        "readiness": app.readiness_url,
        "metrics": app.metrics_url,
    }
    return {name: urlparse(str(url)).hostname for name, url in urls.items() if url is not None}


def test_production_registry_uses_no_retired_hosts() -> None:
    for app in get_registry("production"):
        for name, host in _hosts(app).items():
            assert host not in RETIRED_HOSTS, f"{app.id} {name}_url uses retired host {host}"


def test_single_container_apps_use_one_host_for_every_url() -> None:
    for app in get_registry("production"):
        if app.id in SINGLE_HOST_APPS:
            assert len(set(_hosts(app).values())) == 1, f"{app.id} spans {_hosts(app)}"
