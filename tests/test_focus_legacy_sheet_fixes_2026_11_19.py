"""
Focus Legacy use-case sheet re-test 2026-11-19 (docs/Focus_Legacy_UseCase_Test_Report_2026-11-19.xlsx):
KI-693 (a group named after a CM Elevate sector), KI-686 / KI-694 (list key points), KI-695 (a
dangling "From the scheme FAQ: 4."), KI-696 (a record's own figure called a "recorded total").
Real functions; the DB / group lookup is stubbed where one is needed.
"""
import asyncio

from app import pipeline as p
from app import rag


# ── KI-695: numbered FAQ headings ────────────────────────────────────────────────────────
# megh_knowledge stores an FAQ entry as "4. What is a Producer Group (PG)?\n<answer>".
FAQ_PG = ("4. What is a Producer Group (PG)?\nA Producer Group is a collective of farmers (or, in urban "
          "areas, other income-generating individuals) who come together to access the scheme's benefits.")
FAQ_MONEY = ("6. How much financial assistance does FOCUS provide?\nEach Producer Group member is given an "
             "initial mobilisation fund of **₹5,000**, intended as seed/working capital.")


def test_numbered_faq_question_heading_is_dropped():
    assert rag._rag_drop_question_heading(FAQ_PG).startswith("A Producer Group is a collective")
    assert rag._rag_drop_question_heading("8a. How do I apply?\nAs a group.") == "As a group."
    # the '#' form still works, and a numbered line that is not a question is kept
    assert rag._rag_drop_question_heading("### 4. What is a PG?\nA group.") == "A group."
    assert rag._rag_drop_question_heading("1. Form a group.\n2. Register.") == "1. Form a group.\n2. Register."
    assert rag._rag_drop_question_heading("2021 was the year?\nYes.") == "2021 was the year?\nYes."


def test_faq_facts_never_append_an_entry_number():
    answer = "Under FOCUS, Producer Groups are the collective unit through which members access benefits."
    for text in (FAQ_PG, FAQ_MONEY):
        out = rag._with_faq_facts(answer, [{"faq_match": True, "text": text}])
        assert "From the scheme FAQ: 4." not in out and "From the scheme FAQ: 6." not in out
    # a real fact with a missing number is still added (CFC case, 2026-10-29)
    out = rag._with_faq_facts(answer, [{"faq_match": True, "text": FAQ_MONEY}])
    assert "₹5,000" in out and out.count("From the scheme FAQ") == 1


# ── KI-686: the row item is the column that names every row once ───────────────────────────
TC19_ROWS = [{"pg_name": f"Group {i}", "lgd_district": ["EAST KHASI HILLS", "RI BHOI", "WEST GARO HILLS"][i % 3],
              "payments": 2} for i in range(9)]


def test_key_points_count_groups_not_districts():
    pts = "\n".join(p._c12_key_points(TC19_ROWS))
    assert "districts" not in pts.split("\n")[0]           # was "across 9 districts"
    assert "Spread over 3 districts" in pts
    assert "Every district has" not in pts


def test_key_points_programme_by_district_rows_are_rows():
    # CM Elevate OFF-027 (KI-686): 2 programmes x 2 districts read "across 4 districts"
    rows = [{"scheme_name": s, "lgd_district": d, "applicants": n} for s, d, n in (
        ("Meghalaya Piggery Development Scheme", "RI BHOI", 1474), ("Meghalaya Piggery Development Scheme", "WEST GARO HILLS", 184),
        ("Meghalaya Poultry Farming Scheme", "RI BHOI", 138), ("Meghalaya Poultry Farming Scheme", "WEST GARO HILLS", 32))]
    pts = p._c12_key_points(rows)
    assert pts[0] == "- Applicants: 1,828 in total, across 4 rows."
    assert any("2 districts" in x for x in pts) and not any("4 districts" in x for x in pts)
    assert any(x.startswith("- Highest single row: 1,474") for x in pts)


def test_key_points_hierarchical_lists_unchanged():
    rows = [{"lgd_district": "A", "lgd_block": "X", "lgd_village_name": "V1", "houses": 1},
            {"lgd_district": "A", "lgd_block": "X", "lgd_village_name": "V2", "houses": 2},
            {"lgd_district": "B", "lgd_block": "Y", "lgd_village_name": "V3", "houses": 4}]
    pts = p._c12_key_points(rows)
    assert pts[0] == "- Houses: 7 in total, across 3 villages."
    assert "- Spread over 2 districts and 2 blocks." in pts


# ── KI-694: a list cut off by its LIMIT ──────────────────────────────────────────────────
def test_key_points_of_a_truncated_list_say_they_cover_the_rows_shown():
    sql = "SELECT pg_name, lgd_district, payments FROM curated.v_focus_legacy ORDER BY 3 DESC LIMIT 9"
    out = p._framed_fallback(TC19_ROWS, ["Focus Legacy"], {}, sql=sql)
    assert "**Key points (the 9 rows shown)**" in out
    # not cut off (no LIMIT, or fewer rows than it): the plain heading
    out = p._framed_fallback(TC19_ROWS, ["Focus Legacy"], {}, sql=sql.replace("LIMIT 9", "LIMIT 100"))
    assert "**Key points**\n" in out


def test_truncated_list_money_is_summed_over_the_whole_result(monkeypatch):
    seen = []

    async def fake_run(sql, *a, **k):
        seen.append(sql)
        return [{"s0": 95440000}]
    monkeypatch.setattr(p, "run_readonly", fake_run)
    # live: the catalogue (via _c13_money_units) records amount_disbursed in rupees
    def catalogue(result):
        result["data"] = [{(k + "_rs" if k == "amount_disbursed" else k): v for k, v in r.items()}
                          for r in result["data"]]
    monkeypatch.setattr(p, "_c13_money_units", catalogue)
    rows = [{"date_of_remittance": "2025-06-18", "pg_id": "PG-1", "no_of_pg_members": 3, "amount_disbursed": 15000}] * 3
    sql = ("SELECT date_of_remittance, pg_id, no_of_pg_members, amount_disbursed FROM curated.v_focus_legacy "
           "WHERE date_of_remittance >= DATE '2025-04-01' ORDER BY date_of_remittance LIMIT 3")
    out = asyncio.run(p._focus_legacy_list_sums(sql, rows))
    assert out == "₹9,54,40,000 (≈ ₹9.54 crore) amount disbursed"
    assert "LIMIT 3" not in seen[0] and 'SUM(q."amount_disbursed")' in seen[0]
    assert 'SUM(q."no_of_pg_members")' not in seen[0]         # money only
    # a name that already carries its unit (the SQL-prompt convention) needs no catalogue
    monkeypatch.setattr(p, "_c13_money_units", lambda result: None)
    seen.clear()
    out = asyncio.run(p._focus_legacy_list_sums(sql, [{"pg_id": "PG-1", "amount_rupees": 5000}] * 3))
    assert out.startswith("₹9,54,40,000") and 'SUM(q."amount_rupees")' in seen[0]
    # no money column known: nothing is queried, nothing is said
    seen.clear()
    assert asyncio.run(p._focus_legacy_list_sums(sql, [{"pg_id": "PG-1", "no_of_pg_members": 3}] * 3)) == ""
    assert seen == []

    async def boom(sql, *a, **k):
        raise RuntimeError("db down")
    monkeypatch.setattr(p, "run_readonly", boom)
    assert asyncio.run(p._focus_legacy_list_sums(sql, rows)) == ""


# ── KI-696: one record's own figure ──────────────────────────────────────────────────────
def test_a_max_figure_is_not_a_recorded_total():
    row = [{"pg_id": "PG-FOCUS-WKH-3565", "pg_name": "Nongprat Lynti", "group_size": 190}]
    sql = ("SELECT pg_id, MAX(pg_name) AS pg_name, MAX(no_of_pg_members) AS group_size FROM curated.v_focus_legacy "
           "GROUP BY pg_id HAVING MAX(no_of_pg_members) > 20 ORDER BY group_size DESC LIMIT 10")
    out = p._framed_fallback(row, ["Focus Legacy"], {}, sql=sql)
    assert "the group size is 190." in out and "recorded total" not in out
    # without the SQL, or for a SUM, the total wording stays (a village's women count, MGNREGA UAT)
    assert "recorded total" in p._framed_fallback(row, ["Focus Legacy"], {})
    assert "recorded total" in p._framed_fallback(row, ["Focus Legacy"], {}, sql=sql.replace(
        "MAX(no_of_pg_members) AS group_size", "SUM(no_of_pg_members) AS group_size"))
    # a category total and a plural count keep the pinned wording
    out = p._framed_fallback([{"house_status": "Completed", "houses": 6847}], ["PMAY-G"],
                             {"district": "RI BHOI", "year": "FY 2023-24"})
    assert out == "Under PMAY-G, for Completed, in FY 2023-24 in Ri Bhoi district, the recorded total is 6,847 houses."


def test_hedge_safety_net_keeps_the_max_wording(monkeypatch):
    # live TC-15: the composer hedged ("does not cover the top 10 list"), the safety net wrote
    # the deterministic answer — without the SQL it said "the recorded total is 190 group size"
    async def composer(prompt):
        return ("Nongprat Lynti has 190 members across all financial years. The data available does not "
                "cover the top 10 list requested as only one PG meets the criteria.")
    monkeypatch.setattr(p.llm, "call_response_composer", composer)
    sql = ("SELECT pg_id, MAX(pg_name) AS pg_name, MAX(no_of_pg_members) AS group_size FROM curated.v_focus_legacy "
           "GROUP BY pg_id HAVING MAX(no_of_pg_members) > 20 ORDER BY group_size DESC NULLS LAST LIMIT 10")
    out = asyncio.run(p.compose_response("List top 10 PGs which has more than 20 members.", sql,
                                         [{"pg_id": "PG-FOCUS-WKH-3565", "pg_name": "Nongprat Lynti", "group_size": 190}],
                                         schemes=["Focus Legacy"], entities={}))
    assert "190" in out and "190 group size" not in out


def test_fallback_detection_matches_the_sql_wording():
    row = [{"pg_id": "PG-1", "group_size": 9}]
    sql = "SELECT pg_id, MAX(no_of_pg_members) AS group_size FROM curated.v_focus_legacy GROUP BY pg_id"
    framed = p._framed_fallback(row, ["CM Elevate Legacy"], {}, sql=sql)
    assert p._is_fallback_answer(framed, row, ["CM Elevate Legacy"], {}, sql=sql)
    assert p._is_fallback_answer(p._framed_fallback(row, ["CM Elevate Legacy"], {}), row, ["CM Elevate Legacy"], {})


def test_raw_column_names_are_spotted_as_whole_words():
    rows = [{"producer_groups": 268}]
    assert p._c13_raw_column_named("The result shows 268 for the producer_groups metric.", rows)
    assert p._c13_raw_column_named("268 (`producer_groups`).", rows)
    assert not p._c13_raw_column_named("268 producer groups are mapped to Nongstoin.", rows)
    assert not p._c13_raw_column_named("anything", [{"groups": 3}])        # no underscore name


def test_strict_retry_uses_readable_labels_and_rejects_a_leaked_column(monkeypatch):
    seen = []
    replies = ["The query counts 26,800 Producer Groups.",                          # misquote -> retry
               "The query counts 268 Producer Groups. The result shows 268 for the producer_groups metric."]

    async def composer(prompt):
        seen.append(prompt)
        return replies[min(len(seen), len(replies)) - 1]
    monkeypatch.setattr(p.llm, "call_response_composer", composer)
    out = asyncio.run(p.compose_response(
        "How many Producer Groups are mapped to Nongstoin?",
        "SELECT COUNT(DISTINCT pg_id) AS producer_groups FROM curated.v_focus_legacy",
        [{"producer_groups": 268}], schemes=["Focus Legacy"], entities={"assembly_constituency": "Nongstoin"}))
    assert len(seen) == 2 and "producer groups = 268" in seen[1] and "producer_groups = 268" not in seen[1]
    assert "producer_groups" not in out and "268" in out


# ── KI-697: the Unresolved filter moves onto the village count beside other totals ─────────
TC20_SQL = ("SELECT SUM(amount_disbursed) AS amount_disbursed, SUM(no_of_pg_members) AS memberships, "
            "COUNT(*) AS payments, COUNT(DISTINCT pg_id) AS producer_groups, COUNT(DISTINCT village_code) AS villages "
            "FROM curated.v_focus_legacy WHERE date_of_remittance >= CAST('2025-04-01' AS DATE) "
            "AND date_of_remittance < CAST('2025-07-01' AS DATE) AND entity_type <> 'Unresolved'")


def test_totals_beside_a_village_count_keep_the_no_village_payments():
    out = p._cm_legacy_keep_unresolved_off_village(
        "Show me all remittances made between April and June 2025.", ["Focus Legacy"], TC20_SQL)
    assert "COUNT(DISTINCT village_code) FILTER(WHERE entity_type <> 'Unresolved') AS villages" in out
    where = out.split(" WHERE ", 1)[1].split("FILTER")[0]
    assert "Unresolved" not in where and "2025-04-01" in where and "2025-07-01" in where
    # a question that names villages gets the same, correct, form
    assert p._cm_legacy_keep_unresolved_off_village("villages and payments", ["Focus Legacy"], TC20_SQL) == out


def test_village_lists_and_pure_village_counts_keep_the_where_filter():
    for q, sql in (("How many villages?",
                    "SELECT COUNT(DISTINCT village_code) FROM curated.v_focus_legacy WHERE entity_type <> 'Unresolved'"),
                   ("payments per village", "SELECT lgd_village_name, COUNT(*) AS n FROM curated.v_focus_legacy "
                                            "WHERE entity_type <> 'Unresolved' GROUP BY lgd_village_name")):
        assert p._cm_legacy_keep_unresolved_off_village(q, ["Focus Legacy"], sql) == sql
    # other schemes are never touched
    assert p._cm_legacy_keep_unresolved_off_village("x", ["PMAY-G"], TC20_SQL) == TC20_SQL


# ── KI-693: a group named after a CM Elevate sector ──────────────────────────────────────
def _stub_groups(monkeypatch, names):
    calls = []

    async def fake_answer(question, scope=None):
        calls.append(question)
        data = [{"pg_id": f"PG-{i}", "pg_name": n} for i, n in enumerate(names)]
        return {"route": "data", "schemes": ["Focus Legacy"], "data": data, "answer": "x"}
    monkeypatch.setattr(p, "_focus_legacy_pg_name_answer", fake_answer)
    return calls


def test_exact_group_named_after_a_sector_is_answered_as_the_group(monkeypatch):
    q = "How many members are there in Balmora Piggery?"
    assert p._names_cm_elevate(q)                        # the words alone still read CM Elevate
    _stub_groups(monkeypatch, ["Balmora Piggery"])
    assert asyncio.run(p._focus_legacy_exact_group_answer(q))["schemes"] == ["Focus Legacy"]


def test_no_exact_group_or_a_bare_sector_keeps_the_cm_elevate_pause(monkeypatch):
    calls = _stub_groups(monkeypatch, ["Balmora Piggery Producer Group Two", "Other Piggery"])
    # only partial matches: no exact group -> None (the pause stays)
    assert asyncio.run(p._focus_legacy_exact_group_answer("How many members are there in Balmora Piggery?")) is None
    _stub_groups(monkeypatch, ["Piggery"])
    for q in ("How many members are there in piggery?", "How many members in Poultry?"):
        assert asyncio.run(p._focus_legacy_exact_group_answer(q)) is None
    # a question naming a scheme is never taken
    assert asyncio.run(p._focus_legacy_exact_group_answer(
        "How many members are there in Balmora Piggery under CM Elevate?")) is None
    assert calls == [] or all("CM Elevate" not in c for c in calls)
