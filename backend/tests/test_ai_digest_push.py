import importlib.util
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from app.schemas import DigestIn

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


push = _load("ai_digest_push")
llm = _load("ai_digest_llm")

NOW = datetime(2026, 10, 3, 11, 0, tzinfo=timezone.utc)
CONFIG = {
    "interests": ["building with AI"],
    "max_age_hours": 36,
    "max_items_per_source": 2,
    "max_candidates": 10,
    "max_digest_items": 3,
    "sources": [],
}
RSS = b"""<rss version="2.0"><channel>
<item><title>Post A</title><link>https://a.example/post-a?utm_source=x</link>
<pubDate>Fri, 02 Oct 2026 12:00:00 GMT</pubDate>
<description>&lt;p&gt;Hello &lt;b&gt;world&lt;/b&gt;
&lt;script&gt;bad()&lt;/script&gt;&lt;/p&gt;</description></item>
<item><title>No link here</title></item>
</channel></rss>"""
ATOM = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Atom post</title>
<link rel="self" href="https://b.example/self"/>
<link rel="alternate" href="https://b.example/atom"/>
<updated>2026-10-02T09:00:00Z</updated><content type="html">&lt;p&gt;Body text&lt;/p&gt;</content>
</entry></feed>"""


def _src(name="Blog", weight=1.0):
    return {"name": name, "weight": weight}


def _cand(i, excerpt="Some excerpt.", hours_ago=5, source="Blog", **signals):
    return {
        "id": i, "source": source, "weight": 1.0, "title": f"Title {i}",
        "url": f"https://example.com/{i}", "published_at": NOW - timedelta(hours=hours_ago),
        "excerpt": excerpt, "signals": signals,
    }


def _output(items, headline="Lead story [1]."):
    return json.dumps({"headline": headline, "items": items})


def _entry(i, **over):
    return {"id": i, "category": "systems", "priority": 4, "summary": "A summary.",
            "why_it_matters": "Because.", **over}


# ---------------------------------------------------------------- parsing


def test_strip_html_removes_tags_scripts_and_entities():
    assert push.strip_html("<p>Hi &amp; <b>bye</b><script>x()</script></p>") == "Hi & bye"
    assert push.strip_html(None) == ""


def test_canonical_url_drops_tracking_fragment_and_trailing_slash():
    a = push.canonical_url("https://Example.com/post/?utm_source=x&id=7#top")
    assert a == "https://example.com/post?id=7"
    plain = push.canonical_url("https://example.com/post")
    assert plain == push.canonical_url("https://example.com/post/")
    assert push.canonical_url("javascript:alert(1)") == ""
    assert push.canonical_url("ftp://example.com/x") == ""


def test_parse_feed_rss_skips_items_without_a_link_and_cleans_body():
    items = push.parse_feed(RSS, _src())
    assert len(items) == 1
    assert items[0]["title"] == "Post A" and items[0]["excerpt"] == "Hello world"
    assert items[0]["published_at"] == datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)


def test_parse_feed_atom_prefers_the_alternate_link():
    (item,) = push.parse_feed(ATOM, _src())
    assert item["url"] == "https://b.example/atom" and item["excerpt"] == "Body text"
    assert item["published_at"] == datetime(2026, 10, 2, 9, 0, tzinfo=timezone.utc)


def test_parse_feed_rejects_non_xml():
    try:
        push.parse_feed(b"<html><body>blocked", _src())
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_parse_hn_falls_back_to_the_discussion_url_and_keeps_points():
    data = {"hits": [
        {"title": "Show HN: thing", "url": None, "objectID": "42", "points": 120,
         "num_comments": 9, "created_at_i": 1_790_000_000, "story_text": "<p>I built it</p>"},
        {"title": None, "objectID": "43", "created_at_i": 1_790_000_000},
    ]}
    (item,) = push.parse_hn(data, _src("HN"))
    assert item["url"] == "https://news.ycombinator.com/item?id=42"
    assert item["signals"] == {"hn_points": 120, "hn_comments": 9}
    assert item["excerpt"] == "I built it"


def test_parse_hf_papers():
    data = [{"paper": {"id": "2610.00001", "title": "A paper", "summary": "Abstract.",
                       "publishedAt": "2026-10-02T00:00:00.000Z", "upvotes": 31}}, {"paper": {}}]
    (item,) = push.parse_hf_papers(data, _src("HF"))
    assert item["url"] == "https://huggingface.co/papers/2610.00001"
    assert item["signals"] == {"upvotes": 31}


# ---------------------------------------------------------------- collecting and selecting


def test_a_failing_source_is_recorded_and_does_not_stop_the_others():
    config = {**CONFIG, "sources": [
        {"name": "Good", "type": "rss", "url": "https://good.example/feed"},
        {"name": "Bad", "type": "rss", "url": "https://bad.example/feed"},
    ]}

    def fake(url):
        if "bad" in url:
            raise OSError("HTTP Error 403: Forbidden")
        return RSS

    items, stats = push.collect(config, NOW, fetch=fake)
    assert len(items) == 1 and stats["Good"] == {"fetched": 1, "error": None}
    assert stats["Bad"]["fetched"] == 0 and "403" in stats["Bad"]["error"]


def test_select_filters_age_dedupes_merges_signals_caps_and_numbers():
    items = [
        {**_cand(0, hours_ago=2), "title": "Fresh"},
        {**_cand(0, hours_ago=100), "title": "Old", "url": "https://example.com/old"},
        {**_cand(0, hours_ago=3), "title": "Undated", "url": "https://example.com/u",
         "published_at": None},
        # same story from two sources: the heavier source wins and inherits the HN points
        {**_cand(0, hours_ago=4, source="Blog"), "title": "Dup",
         "url": "https://example.com/dup?utm_source=a"},
        {**_cand(0, hours_ago=4, source="HN", hn_points=300), "weight": 0.5,
         "url": "https://example.com/dup/", "title": "Dup on HN"},
        {**_cand(0, hours_ago=1), "url": "https://example.com/c", "title": "C"},
        {**_cand(0, hours_ago=1), "url": "https://example.com/d", "title": "D"},
    ]
    stats = {"Blog": {"fetched": 6, "error": None}, "HN": {"fetched": 1, "error": None}}
    picked = push.select_candidates(items, CONFIG, NOW, stats)
    titles = [p["title"] for p in picked]
    assert "Old" not in titles and "Undated" not in titles and "Dup on HN" not in titles
    assert sum(1 for p in picked if p["source"] == "Blog") == 2  # per-source cap
    assert [p["id"] for p in picked] == list(range(1, len(picked) + 1))
    assert stats["Blog"]["recent"] == 4 and stats["HN"]["recent"] == 1


def test_dedupe_keeps_the_hn_points_signal():
    blog = {**_cand(0, hours_ago=4), "url": "https://example.com/dup", "title": "Dup"}
    hn = {**_cand(0, hours_ago=4, source="HN", hn_points=300), "weight": 0.5,
          "url": "https://example.com/dup?utm_medium=x", "title": "Dup on HN"}
    (picked,) = push.select_candidates([hn, blog], CONFIG, NOW)
    assert picked["title"] == "Dup" and picked["signals"] == {"hn_points": 300}


# ---------------------------------------------------------------- model output


def test_unknown_and_duplicate_ids_are_dropped():
    cands = [_cand(1), _cand(2)]
    out = _output([_entry(1), _entry(1, summary="again"), _entry(99), _entry(True), _entry("x")])
    headline, ranked = push.parse_model_output(out, cands, CONFIG)
    assert [r["id"] for r in ranked] == [1] and ranked[0]["summary"] == "A summary."


def test_code_fences_and_prose_around_the_json_are_tolerated():
    cands = [_cand(1)]
    fenced = "Here you go:\n```json\n" + _output([_entry(1)]) + "\n```"
    _, ranked = push.parse_model_output(fenced, cands, CONFIG)
    assert len(ranked) == 1


def test_urls_are_stripped_priority_clamped_and_category_defaulted():
    cands = [_cand(1), _cand(2)]
    out = _output([
        _entry(1, summary="See https://evil.example/x for more.", priority=9),
        _entry(2, category="gossip", priority="high"),
    ])
    _, ranked = push.parse_model_output(out, cands, CONFIG)
    by_id = {r["id"]: r for r in ranked}
    assert "http" not in by_id[1]["summary"] and by_id[1]["priority"] == 5
    assert by_id[2]["priority"] == 2 and by_id[2]["category"] == "news"


def test_title_only_items_are_flagged_and_capped_at_priority_three():
    cands = [_cand(1, excerpt="")]
    _, ranked = push.parse_model_output(_output([_entry(1, priority=5)]), cands, CONFIG)
    assert ranked[0]["priority"] == 3 and ranked[0]["summary"].startswith("Title only:")


def test_ranking_and_cap_and_headline_markers_for_dropped_items_are_removed():
    cands = [_cand(i, hours_ago=i) for i in range(1, 6)]
    entries = [_entry(i, priority=p) for i, p in zip(range(1, 6), (2, 5, 4, 3, 1))]
    headline, ranked = push.parse_model_output(
        _output(entries, headline="Big news [2] and [3], not [5] or [42]."), cands, CONFIG
    )
    assert [r["id"] for r in ranked] == [2, 3, 4]  # top 3 by priority
    assert headline == "Big news [2] and [3], not or ."


def test_unusable_output_raises():
    for bad in ("no json at all", "{not json}", _output([]), _output([_entry(99)])):
        try:
            push.parse_model_output(bad, [_cand(1)], CONFIG)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {bad!r}")


def test_citations_come_from_the_feed_never_from_the_model():
    cands = [_cand(1)]
    sneaky = _entry(1, url="https://evil.example", title="Fake title", source="Fake")
    headline, ranked = push.parse_model_output(_output([sneaky]), cands, CONFIG)
    payload = push.build_payload(date(2026, 10, 3), NOW, "anthropic/x", headline, ranked, cands, {})
    item = payload["items"][0]
    assert item["url"] == "https://example.com/1" and item["title"] == "Title 1"
    assert item["source"] == "Blog"


def test_built_payload_satisfies_the_backend_schema():
    cands = [_cand(1), _cand(2, hours_ago=9)]
    headline, ranked = push.parse_model_output(
        _output([_entry(1), _entry(2, priority=2)], headline="Both [1] [2]."), cands, CONFIG
    )
    payload = push.build_payload(date(2026, 10, 3), NOW, "anthropic/x", headline, ranked, cands,
                                 {"Blog": {"fetched": 2, "error": None}})
    parsed = DigestIn.model_validate(payload)
    assert [i.id for i in parsed.items] == [1, 2] and parsed.digest_date == date(2026, 10, 3)


def test_the_prompt_lists_every_candidate_by_id_and_the_interests():
    cands = [_cand(1, hn_points=50), _cand(2, excerpt="")]
    system, user = push.build_prompt(cands, CONFIG, date(2026, 10, 3))
    assert "at most 3 items" in system and "Never write URLs" in system
    assert "[1] source: Blog" in user and "hn_points=50" in user and "excerpt: (none)" in user
    assert "- building with AI" in user


# ---------------------------------------------------------------- llm provider selection


def test_provider_resolution_and_missing_configuration():
    assert llm.resolve({}) == ("anthropic", "claude-sonnet-5-5")
    openai_env = {"DIGEST_LLM_PROVIDER": "OpenAI", "DIGEST_LLM_MODEL": "m"}
    assert llm.resolve(openai_env) == ("openai", "m")
    for env, needle in (
        ({"DIGEST_LLM_PROVIDER": "nope"}, "Unknown"),
        ({"DIGEST_LLM_PROVIDER": "openai"}, "DIGEST_LLM_MODEL"),
        ({}, "ANTHROPIC_API_KEY"),
    ):
        try:
            llm.complete("s", "u", env=env)
        except llm.LLMError as exc:
            assert needle in str(exc)
        else:
            raise AssertionError(f"expected LLMError for {env}")


def test_a_provider_can_be_swapped_in_without_touching_the_pipeline():
    original = llm.PROVIDERS.copy()
    try:
        fake = lambda model, system, user, key, mt, to: f"{model}:{key}"  # noqa: E731
        llm.PROVIDERS["fake"] = (fake, "FAKE_KEY", "m1")
        text, label = llm.complete("s", "u", env={"DIGEST_LLM_PROVIDER": "fake", "FAKE_KEY": "k"})
        assert (text, label) == ("m1:k", "fake/m1")
    finally:
        llm.PROVIDERS.clear()
        llm.PROVIDERS.update(original)


# ---------------------------------------------------------------- end to end


def _run_main(argv, items, stats, completion, pushed):
    saved = (push.collect, push.ai_digest_llm.complete, push.push_common.post_json,
             push.push_common.load_config, push.time.sleep)
    push.collect = lambda config, now: (items, stats)
    push.ai_digest_llm.complete = completion
    def record(path, payload, config, timeout=10):
        pushed.append((path, payload))
        return True

    push.push_common.post_json = record
    push.push_common.load_config = lambda: {}
    push.time.sleep = lambda s: None
    try:
        return push.main(argv)
    finally:
        (push.collect, push.ai_digest_llm.complete, push.push_common.post_json,
         push.push_common.load_config, push.time.sleep) = saved


def _now_utc_items():
    # main() uses the real clock, so build items relative to it
    now = datetime.now(timezone.utc)
    published = now - timedelta(hours=1)
    return [{**_cand(0), "url": "https://example.com/a", "title": "A", "published_at": published}]


def test_main_pushes_a_validated_digest_to_the_ingest_endpoint():
    pushed = []
    ok = lambda system, user: (_output([_entry(1)]), "anthropic/test")  # noqa: E731
    stats = {"Blog": {"fetched": 1, "error": None}}
    code = _run_main(["--date", "2026-10-03"], _now_utc_items(), stats, ok, pushed)
    assert code == 0 and pushed[0][0] == "/internal/ai-digest/sync"
    DigestIn.model_validate(pushed[0][1])


def test_main_does_not_push_when_the_model_output_is_unusable_or_every_source_failed():
    pushed = []
    bad = lambda system, user: ("garbage", "anthropic/test")  # noqa: E731
    live = {"Blog": {"fetched": 1, "error": None}}
    assert _run_main([], _now_utc_items(), live, bad, pushed) == 1
    dead = {"Blog": {"fetched": 0, "error": "OSError: HTTP Error 403"}}
    assert _run_main([], [], dead, bad, pushed) == 1
    assert pushed == []


def test_dry_run_and_empty_windows_make_no_llm_call_and_no_push():
    pushed = []

    def boom(system, user):
        raise AssertionError("LLM must not be called")

    stats = {"Blog": {"fetched": 1, "error": None}}
    assert _run_main(["--dry-run"], _now_utc_items(), stats, boom, pushed) == 0
    assert _run_main([], [], stats, boom, pushed) == 0
    assert pushed == []
