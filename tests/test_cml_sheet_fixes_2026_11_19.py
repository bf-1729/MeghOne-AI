"""CM Elevate Legacy use-case sheet re-test 2026-11-19 (KI-687..692): regression tests on the
real functions. Rows are the live megh_db results of the failing turns (DB = raw export)."""
import asyncio

from app import llm
from app import pipeline as p
from app.session_store import Turn

FY_SQL = ("SELECT COALESCE(financial_year_short, '(no financial year)') AS financial_year, COUNT(*) AS records, "
          "ROUND(SUM(sanctioned_amount) / 1e7, 2) AS sanctioned_cr, ROUND(SUM(total_subsidy_disbursement) / 1e7, 2) "
          "AS subsidy_cr, ROUND(SUM(total_loan_disbursement) / 1e7, 2) AS loan_cr, ROUND(SUM(total_disbursement) / 1e7, 2) "
          "AS total_disbursed_cr FROM curated.v_cm_elevate_disbursement GROUP BY financial_year_short "
          "ORDER BY financial_year_short")
FY_ROWS = [
    {"financial_year": "(no financial year)", "records": 395, "sanctioned_cr": 5.43, "subsidy_cr": 0.52,
     "loan_cr": 0.07, "total_disbursed_cr": 0.59},
    {"financial_year": "2024-25", "records": 2291, "sanctioned_cr": 105.16, "subsidy_cr": 38.92,
     "loan_cr": 20.9, "total_disbursed_cr": 59.82},
    {"financial_year": "2025-26", "records": 137, "sanctioned_cr": 32.15, "subsidy_cr": 13.12,
     "loan_cr": 9.37, "total_disbursed_cr": 22.49},
]
SCHEME_SQL = ("SELECT scheme_name, ROUND(SUM(total_disbursement) / 1e7, 2) AS total_disbursed_cr "
              "FROM curated.v_cm_elevate_disbursement GROUP BY scheme_name ORDER BY total_disbursed_cr DESC")
SCHEME_ROWS = [("Meghalaya Agriculture Warehouse Scheme", 226180213.25), ("Prime Tourism Vehicle Scheme", 143144935.6),
               ("Prime Agriculture Response Vehicle Scheme", 142058851.9),
               ("Meghalaya Piggery Development Scheme", 95241250.0), ("Meghalaya Sports & Wellness Scheme", 58700000.0),
               ("Meghalaya Any Business Venture Scheme", 53831586.0),
               ("Meghalaya Common Facility Center Scheme", 44223729.0), ("Meghalaya Poultry Farming Scheme", 40067000.0),
               ("Meghalaya Dairy Development Scheme", 12710752.0),
               ("Meghalaya Sericulture & Weaving Scheme(weaving)", 5874220.0), ("Meghalaya Motorcaravan Scheme", 5000000.0),
               ("Meghalaya Goat Farming Scheme", 1920000.0),
               ("Meghalaya Sericulture & Weaving Scheme (spinning)", 26000.0)]


def _rounded():
    return [{"scheme_name": s, "total_disbursed_cr": round(v / 1e7, 2)} for s, v in SCHEME_ROWS]


def _exact():
    return [{"scheme_name": s, "total_disbursed_cr": v / 1e7} for s, v in SCHEME_ROWS]


# ── KI-691: a rounded crore figure is never re-expanded to "exact" rupees ─────────────
def test_rounded_small_crore_stays_in_crore():
    assert p._c12_money(0.07, "crore") == "₹0.07 crore"            # was "₹7,00,000 (≈ ₹7.00 lakh)"
    assert p._c12_money(0.05, "lakh") == "₹5,000"                  # lakh is a stored unit: exact, unchanged


def test_unrounded_small_crore_gives_exact_rupees():
    assert p._c12_money(0.0666, "crore") == "₹6,66,000 (≈ ₹6.66 lakh)"
    assert p._c12_money(0.0026, "crore") == "₹26,000"


def test_unchanged_money_formats():
    assert p._c12_money(0, "crore") == "₹0"
    assert p._c12_money(82.8979, "crore") == "₹82.90 crore"
    assert p._c12_money(35000) == "₹35,000"
    assert p._c12_money(940000) == "₹9,40,000 (≈ ₹9.40 lakh)"
    assert p._c12_money(9.4, "lakh") == "₹9.40 lakh"


# ── KI-687: the trend leads with the measure the question names ────────────────────────
def test_trend_leads_with_the_asked_measure():
    q = "What was the total disbursement in each financial year?"
    shape = p._answer_shape(q, FY_SQL, FY_ROWS)
    assert shape.kind == "trend" and shape.metric == "total_disbursed_cr"
    body = p._c12s_e9_body(shape, FY_ROWS, q)
    assert "₹59.82 crore in FY 2024-25 to ₹22.49 crore in FY 2025-26" in body
    assert "- FY 2024-25: ₹59.82 crore" in body and "- (no financial year): ₹0.59 crore" in body


def test_trend_keeps_the_first_measure_when_the_question_names_it():
    q = "How many applications are recorded for each financial year?"
    assert p._answer_shape(q, FY_SQL, FY_ROWS).metric == "records"
    q = "How many records were sanctioned and disbursed in each financial year?"   # two named: no switch
    assert p._answer_shape(q, FY_SQL, FY_ROWS).metric == "records"


# ── KI-688: an undated bucket is not a period ─────────────────────────────────────────
def test_trend_movement_skips_the_no_year_bucket():
    q = "How many applications are recorded for each financial year?"
    shape = p._answer_shape(q, FY_SQL, FY_ROWS)
    body = p._c12s_e9_body(shape, FY_ROWS, q)
    assert body.splitlines()[0] == "Records fell from 2,291 in FY 2024-25 to 137 in FY 2025-26, down 2,154 (94.0%)."
    assert "from 395" not in body
    assert body.splitlines()[-1].startswith("- (no financial year): 395")
    facts, _nums = p._shape_facts(shape, FY_ROWS)
    assert "2,291 in 2024-25 -> 137 in 2025-26" in facts
    fb = p._shaped_fallback(shape, FY_ROWS, ["CM Elevate Legacy"], {}, q)
    assert "from 395" not in fb and "2,291" in fb


def test_time_order_keeps_month_name_trends():
    pairs = [({"month": "Mar"}, 3), ({"month": "Apr"}, 1)]
    dated, undated = p._c12s_time_order(pairs, "month")
    assert [r["month"] for r, _v in dated] == ["Apr", "Mar"] and undated == []


# ── KI-689 / KI-690: code's figures come from the unrounded rows ──────────────────────
def test_breakdown_from_exact_rows_states_the_true_total_and_small_amount():
    q = "What is the total amount disbursed under each scheme?"
    shape = p._answer_shape(q, SCHEME_SQL, _rounded())
    rounded_body = p._c12s_e9_body(shape, _rounded(), q)
    assert "₹82.89 crore" in rounded_body                 # the old defect, from rounded rows
    body = p._c12s_e9_body(shape, _exact(), q)
    assert body.splitlines()[0].startswith("₹82.90 crore total disbursed in total across 13")
    assert "is the smallest with ₹26,000" in body
    assert "- **Meghalaya Sericulture & Weaving Scheme (spinning)** — ₹26,000" in body
    assert "- **Meghalaya Agriculture Warehouse Scheme** — ₹22.62 crore" in body


def test_compose_response_uses_exact_rows_only_for_the_text(monkeypatch):
    async def composer(prompt, **_kw):
        return "Total disbursed by scheme under CM Elevate Legacy:"
    monkeypatch.setattr(llm, "call_response_composer", composer)
    monkeypatch.setattr(p.settings, "ANSWER_TEMPLATES_ENABLED", True)        # conftest turns E9 off
    rows = _rounded()
    answer = asyncio.run(p.compose_response("What is the total amount disbursed under each scheme?", SCHEME_SQL,
                                            rows, schemes=["CM Elevate Legacy"], exact_rows=_exact()))
    assert "₹82.90 crore" in answer and "₹82.89" not in answer and "₹26,000" in answer
    assert rows == _rounded()                                 # the table's rows are untouched


def test_compose_response_ignores_exact_rows_that_do_not_line_up(monkeypatch):
    async def composer(prompt, **_kw):
        return "Total disbursed by scheme under CM Elevate Legacy:"
    monkeypatch.setattr(llm, "call_response_composer", composer)
    monkeypatch.setattr(p.settings, "ANSWER_TEMPLATES_ENABLED", True)        # conftest turns E9 off
    answer = asyncio.run(p.compose_response("What is the total amount disbursed under each scheme?", SCHEME_SQL,
                                            _rounded(), schemes=["CM Elevate Legacy"], exact_rows=_exact()[:5]))
    assert "₹82.89 crore" in answer                           # unchanged behaviour


def test_unrounded_rows_requery_takes_off_only_the_money_rounds(monkeypatch):
    seen = {}

    async def fake_run(sql, *_a, **_kw):
        seen["sql"] = sql
        return list(reversed(_exact()))                       # any order: matched by label

    monkeypatch.setattr(p, "run_readonly", fake_run)
    out = asyncio.run(p._cm_legacy_unrounded_rows(SCHEME_SQL, _rounded()))
    assert "ROUND" not in seen["sql"].upper() and "GROUP BY" in seen["sql"].upper()
    assert [r["scheme_name"] for r in out] == [r["scheme_name"] for r in _rounded()]
    assert abs(out[-1]["total_disbursed_cr"] - 0.0026) < 1e-9


def test_unrounded_rows_none_when_nothing_to_unround_or_rows_differ(monkeypatch):
    async def fake_run(sql, *_a, **_kw):
        return _exact()[:3]
    monkeypatch.setattr(p, "run_readonly", fake_run)
    assert asyncio.run(p._cm_legacy_unrounded_rows(SCHEME_SQL, _rounded())) is None
    plain = "SELECT scheme_name, COUNT(*) AS records FROM curated.v_cm_elevate_disbursement GROUP BY scheme_name"
    assert asyncio.run(p._cm_legacy_unrounded_rows(plain, [{"scheme_name": "a", "records": 1},
                                                           {"scheme_name": "b", "records": 2}])) is None


# ── KI-692: a follow-up rewrite may not drop the user's breakdown ─────────────────────
def test_dropped_breakdown_detected():
    q = "Compare the number of applications across schemes for FY 2024-25."
    assert p._c01_dropped_breakdown(q, "How many total applications are recorded under CM Elevate Legacy for "
                                       "FY 2024-25?") == {"scheme"}
    assert not p._c01_dropped_breakdown(q, "Compare the number of applications across schemes under CM Elevate "
                                           "Legacy for FY 2024-25.")
    assert not p._c01_dropped_breakdown(q, "How many applications are there in each scheme under CM Elevate "
                                           "Legacy for FY 2024-25?")
    assert not p._c01_dropped_breakdown("What is the average spend per district?", "What is the average spend?")


def test_rewrite_followup_keeps_the_question_when_the_breakdown_is_dropped(monkeypatch):
    async def rewriter(prompt, **_kw):
        return "How many total applications are recorded under CM Elevate Legacy for FY 2024-25?"
    monkeypatch.setattr(llm, "call_rewriter", rewriter)
    prev = Turn(question="How many total applications are recorded under CM Elevate Legacy?",
                raw_question="How many total applications are recorded under CM-ELEVATE?", route="data",
                schemes=["CM Elevate Legacy"], resolved_entities={})
    q = "Compare the number of applications across schemes for FY 2024-25."
    assert asyncio.run(p.rewrite_followup(q, prev)) == q
