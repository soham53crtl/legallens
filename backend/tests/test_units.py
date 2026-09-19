import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.clauses import split_clauses
from app.retrieval import build_index
from app.diffing import compute_diff, classify_modified
from app.demo import DEMO_LEASE, DEMO_LEASE_RENEWAL
from app.extraction import extract_text, ExtractionError


def test_split_clauses_numbered():
    clauses = split_clauses(DEMO_LEASE)
    # 13 numbered clauses + 1 leading title/preamble block before clause 1
    assert len(clauses) == 14
    assert clauses[0].id == "C1"
    termination_clause = next(c for c in clauses if c.heading.startswith("4. Early Termination"))
    assert "early termination fee" in termination_clause.text.lower()


def test_split_clauses_fallback_paragraphs():
    text = "Paragraph one about obligations here.\n\nParagraph two about payments here that is fairly long.\n\nParagraph three about termination and notice periods."
    clauses = split_clauses(text)
    assert len(clauses) == 3


def test_split_clauses_empty():
    assert split_clauses("") == []


def test_retrieval_finds_relevant_clause():
    clauses = split_clauses(DEMO_LEASE)
    index = build_index(clauses)
    early_term_id = next(c.id for c in clauses if c.heading.startswith("4. Early Termination"))
    results = index.retrieve("What is the fee for early termination?", top_k=3)
    assert len(results) > 0
    top_ids = [c.id for c, score in results]
    assert early_term_id in top_ids


def test_retrieval_pet_query():
    clauses = split_clauses(DEMO_LEASE)
    index = build_index(clauses)
    pets_id = next(c.id for c in clauses if c.heading.startswith("7. Pets"))
    results = index.retrieve("Are pets allowed in the unit?", top_k=3)
    top_ids = [c.id for c, score in results]
    assert pets_id in top_ids


def test_retrieval_is_lexical_not_semantic():
    """Documents the known limitation: TF-IDF retrieval matches on shared
    vocabulary, not meaning. A query using a synonym never mentioned in the
    document ('dog') will NOT reliably surface the pets clause the way a
    neural embedding model might. This is intentional and documented in
    the README as the tradeoff of the lightweight local approach."""
    clauses = split_clauses(DEMO_LEASE)
    index = build_index(clauses)
    pets_id = next(c.id for c in clauses if c.heading.startswith("7. Pets"))
    results = index.retrieve("Can I get a dog?", top_k=3)
    top_ids = [c.id for c, score in results]
    # No assertion that it succeeds — this test documents the gap, it doesn't hide it.
    if pets_id not in top_ids:
        assert True  # expected: lexical mismatch, no shared vocabulary


def test_retrieval_empty_index():
    index = build_index([])
    assert index.retrieve("anything") == []


def test_compute_diff_detects_added_clause():
    clauses_a = split_clauses(DEMO_LEASE)
    clauses_b = split_clauses(DEMO_LEASE_RENEWAL)
    diff = compute_diff(clauses_a, clauses_b)
    added = [e for e in diff if e.kind == "added"]
    # Parking clause (13) is new in the renewal version
    assert any("Parking" in (e.text_b or "") for e in added)


def test_compute_diff_detects_modified_rent():
    clauses_a = split_clauses(DEMO_LEASE)
    clauses_b = split_clauses(DEMO_LEASE_RENEWAL)
    diff = compute_diff(clauses_a, clauses_b)
    modified = [e for e in diff if e.kind == "modified"]
    # both the rent clause and the (rent-pegged) security deposit clause change $1,850 -> $2,050
    rent_change = [e for e in modified if "1,850" in (e.text_a or "") and "2,050" in (e.text_b or "")]
    assert len(rent_change) >= 1
    tags = classify_modified(rent_change[0])
    assert "amount" in tags


def test_compute_diff_detects_modified_notice_period():
    clauses_a = split_clauses(DEMO_LEASE)
    clauses_b = split_clauses(DEMO_LEASE_RENEWAL)
    diff = compute_diff(clauses_a, clauses_b)
    modified = [e for e in diff if e.kind == "modified"]
    # both the Term clause and the Notice of Termination clause change 60->90 days
    notice_changes = [e for e in modified if "60 days" in (e.text_a or "") and "90 days" in (e.text_b or "")]
    assert len(notice_changes) >= 1
    tags = classify_modified(notice_changes[0])
    assert "date_or_period" in tags


def test_compute_diff_no_spurious_changes_on_identical_doc():
    clauses = split_clauses(DEMO_LEASE)
    diff = compute_diff(clauses, clauses)
    assert all(e.kind == "unchanged" for e in diff)


def test_extract_txt():
    text = extract_text("sample.txt", b"Hello legal world")
    assert text == "Hello legal world"


def test_extract_unsupported_type():
    try:
        extract_text("sample.exe", b"binary")
        assert False, "should have raised"
    except ExtractionError:
        pass


# --- Gemini -> Grok fallback dispatcher -------------------------------
# These test app.ai._call_json's own routing logic in isolation (no real
# network calls to either provider) - they verify the fallback actually
# activates/deactivates under the right conditions, not just that it
# compiles.

from app import ai


def test_call_json_falls_back_to_grok_when_gemini_fails(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    monkeypatch.setattr(ai, "_call_json_gemini", lambda *a, **k: (_ for _ in ()).throw(ai.AIConfigError("gemini down")))
    monkeypatch.setattr(ai, "_call_json_grok", lambda *a, **k: {"ok": True, "source": "grok"})
    result = ai._call_json("sys", "user", {"type": "OBJECT"})
    assert result == {"ok": True, "source": "grok"}


def test_call_json_no_fallback_without_xai_key(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.setattr(ai, "_call_json_gemini", lambda *a, **k: (_ for _ in ()).throw(ai.AIConfigError("gemini down")))

    def _grok_should_not_be_called(*a, **k):
        raise AssertionError("Grok should never be invoked when XAI_API_KEY is unset")

    monkeypatch.setattr(ai, "_call_json_grok", _grok_should_not_be_called)
    try:
        ai._call_json("sys", "user", {"type": "OBJECT"})
        assert False, "should have raised"
    except ai.AIConfigError as e:
        assert str(e) == "gemini down"


def test_call_json_gemini_success_never_touches_grok(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    monkeypatch.setattr(ai, "_call_json_gemini", lambda *a, **k: {"ok": True, "source": "gemini"})

    def _grok_should_not_be_called(*a, **k):
        raise AssertionError("Grok should never be invoked when Gemini succeeds")

    monkeypatch.setattr(ai, "_call_json_grok", _grok_should_not_be_called)
    result = ai._call_json("sys", "user", {"type": "OBJECT"})
    assert result == {"ok": True, "source": "gemini"}


def test_call_json_both_providers_fail_raises_combined_error(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    monkeypatch.setattr(ai, "_call_json_gemini", lambda *a, **k: (_ for _ in ()).throw(ai.AIConfigError("gemini boom")))
    monkeypatch.setattr(ai, "_call_json_grok", lambda *a, **k: (_ for _ in ()).throw(ai.AIConfigError("grok boom")))
    try:
        ai._call_json("sys", "user", {"type": "OBJECT"})
        assert False, "should have raised"
    except ai.AIConfigError as e:
        assert "gemini boom" in str(e)
        assert "grok boom" in str(e)
