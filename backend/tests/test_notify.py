import httpx

from app.config import Settings
from app.notify import send_coms_notification


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_send_coms_notification_logs_when_topic_unset(monkeypatch, caplog) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("httpx.post should not be called when ntfy_topic is unset")

    monkeypatch.setattr(httpx, "post", fail_if_called)

    with caplog.at_level("WARNING"):
        send_coms_notification(_settings(ntfy_topic=""), "hello")

    assert any("not sent" in record.message for record in caplog.records)


def test_send_coms_notification_posts_when_topic_set(monkeypatch) -> None:
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)

    send_coms_notification(_settings(ntfy_topic="my-topic"), "hello world")

    assert len(calls) == 1
    url, kwargs = calls[0]
    assert url == "https://ntfy.sh/my-topic"
    assert kwargs["content"] == b"hello world"


def test_send_coms_notification_swallows_http_error(monkeypatch, caplog) -> None:
    def fake_post(url, **kwargs):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr(httpx, "post", fake_post)

    with caplog.at_level("ERROR"):
        send_coms_notification(_settings(ntfy_topic="my-topic"), "hello")

    assert any("Failed to send Coms notification" in record.message for record in caplog.records)
