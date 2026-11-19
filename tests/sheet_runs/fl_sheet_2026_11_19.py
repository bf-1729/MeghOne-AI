"""Focus Legacy use-case sheet (Use_Cases_-_Focus.csv, TC-01..TC-28), 2026-11-19.
Asks each question through the live pipeline (tests/sheet_runs/harness.Conv), then records
the independent DB truth (curated.v_focus_legacy, read-only) and the raw-file truth
(Focus Legacy to share to BLH.xlsx, aggregates only: the account / holder columns are never read).
Run from the repo root with the .venv python.  Output: fl_sheet_results.json beside this file."""
import asyncio
import collections
import datetime as dt
import json
import os
import sys

REPO = os.getcwd()
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tests", "sheet_runs"))
from harness import Conv, fetch  # noqa: E402
from app import main as app_main  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
V = "curated.v_focus_legacy"
RAW = os.path.join(REPO, "Focus Legacy to share to BLH.xlsx")
SAFE_COLS = ["pg_id", "name_of_pg", "no_of_pg_members", "amount", "date_of_remittance", "financial_year",
             "mapped_district_lgd_name", "mapped_block_lgd_name", "mapped_village_lgd_name",
             "mapped_constituency_name", "name_of_the_programme_updated"]


def load_raw():
    import openpyxl
    wb = openpyxl.load_workbook(RAW, read_only=True)
    ws = wb.active
    it = ws.iter_rows(values_only=True)
    h = next(it)
    ix = {c: h.index(c) for c in SAFE_COLS}
    out = []
    for r in it:
        d = {c: r[i] for c, i in ix.items()}
        v = d["date_of_remittance"]
        d["date_of_remittance"] = v.date() if isinstance(v, dt.datetime) else None
        out.append(d)
    return out


R = load_raw()
U = lambda s: (s or "").strip().upper()  # noqa: E731


def raw_groups(rows):
    return len({r["pg_id"] for r in rows})


def raw_sum(rows, k):
    return sum(r[k] or 0 for r in rows)


def pick_option(rec, want):
    """want: list of lowercase substrings; first option whose label contains all wins."""
    labels, qs = rec.get("options") or [], rec.get("option_qs") or []
    for l, q in zip(labels, qs):
        if all(w in (l or "").lower() for w in want):
            return l, q
    return None, None


async def converse(questions, prefs):
    """Ask the questions in one conversation; answer pauses as a user would."""
    c = Conv()
    turns = []
    for q in questions:
        rec = await c.ask(q)
        chain = [rec]
        for _ in range(3):
            if rec["kind"] != "pause":
                break
            rule = rec.get("rule") or ""
            lab = None
            for key, want in prefs:
                if key in rule or key == "*":
                    lab, oq = pick_option(rec, want)
                    if lab:
                        break
            if not lab:
                if "focus" in rule or any("legacy" in (l or "").lower() for l in rec.get("options") or []):
                    lab, oq = pick_option(rec, ["legacy"])
            if not lab and rule.startswith("year"):
                lab, oq = pick_option(rec, ["all"])
            if not lab and "scope" in rule:
                lab, oq = pick_option(rec, ["meghalaya"])
            if not lab:
                rec["picked"] = "(no matching option - stopped)"
                break
            rec["picked"] = lab
            rec = await c.ask(oq or lab)
            rec["via_option"] = lab
            chain.append(rec)
        turns.append(chain)
    return turns


async def one(sql, *a):
    r = await fetch(sql, list(a))
    v = list(r[0].values())[0] if r else None
    return float(v) if v is not None else 0.0


async def build_cases():
    C = []

    def add(tc, scen, template, qs, db=None, raw=None, kind="data", prefs=(), extra=None):
        C.append(dict(tc=tc, scenario=scen, template=template, questions=qs, db=db or {}, raw=raw or {},
                      kind=kind, prefs=list(prefs), extra=extra or {}))

    # knowledge
    K = [("TC-01", "Understand the FOCUS scheme", "What is the FOCUS scheme in Meghalaya?"),
         ("TC-02", "Understand the scheme objective", "What is the main objective of FOCUS?"),
         ("TC-03", "Understand beneficiary eligibility", "Who can benefit under the FOCUS scheme?"),
         ("TC-04", "Understand Producer Groups", "What is the role of Producer Groups under FOCUS?"),
         ("TC-05", "Understand financial assistance", "What type of financial assistance is provided under FOCUS?"),
         ("TC-06", "Understand scheme support provided to Producer Groups", "What kind of support does FOCUS provide to Producer Groups?"),
         ("TC-07", "Understand fund distribution", "How is financial assistance distributed under FOCUS?"),
         ("TC-09", "Get a scheme overview for official briefing", "Give me a short overview of FOCUS that I can use for an official briefing.")]
    for tc, s, q in K:
        add(tc, s, q, [q], kind="knowledge")

    tot = dict((await fetch(f"SELECT COUNT(*)::float8 payments, COUNT(DISTINCT pg_id)::float8 groups, "
                            f"SUM(no_of_pg_members)::float8 members, SUM(amount_disbursed)::float8 amount FROM {V}"))[0])
    rtot = dict(payments=len(R), groups=raw_groups(R), members=raw_sum(R, "no_of_pg_members"), amount=raw_sum(R, "amount"))

    add("TC-08", "Understand scheme coverage", "How many Producer Groups have been covered under FOCUS?",
        ["How many Producer Groups have been covered under FOCUS?"],
        db={"groups": tot["groups"]}, raw={"groups": rtot["groups"]}, extra={"key": ["groups"]})
    add("TC-10", "Identify total beneficiaries in the FOCUS scheme",
        "How many total beneficiaries are available under the FOCUS scheme?",
        ["How many total beneficiaries are available under the FOCUS scheme?"], db=tot, raw=rtot,
        extra={"key": ["members"], "any_of": ["members", "groups"]})

    rep = await one(f"SELECT COUNT(*) FROM (SELECT pg_id FROM {V} GROUP BY 1 HAVING COUNT(*)>1) x")
    dupn = await one(f"SELECT COUNT(*) FROM (SELECT LOWER(TRIM(pg_name)) FROM {V} GROUP BY 1 HAVING COUNT(DISTINCT pg_id)>1) x")
    rc = collections.Counter(r["pg_id"] for r in R)
    rn = collections.defaultdict(set)
    for r in R:
        rn[(r["name_of_pg"] or "").strip().lower()].add(r["pg_id"])
    add("TC-11+12", "Identify unique Producer Groups, then duplicate Producer Groups (follow-up)",
        "How many unique Producer Groups are present under FOCUS scheme? -> Are there any duplicate Producer Groups there?",
        ["How many unique Producer Groups are present under FOCUS scheme?", "Are there any duplicate Producer Groups there?"],
        db={"groups": tot["groups"], "groups_paid_more_than_once": rep, "extra_payments": tot["payments"] - tot["groups"],
            "names_shared_by_2plus_ids": dupn},
        raw={"groups": rtot["groups"], "groups_paid_more_than_once": sum(1 for v in rc.values() if v > 1),
             "extra_payments": rtot["payments"] - rtot["groups"], "names_shared_by_2plus_ids": sum(1 for v in rn.values() if len(v) > 1)})

    n = await one(f"SELECT COUNT(DISTINCT pg_id) FROM {V} WHERE pg_name ILIKE '%nongstoin%'")
    add("TC-13", "Search for a Producer Group by name", "Is there any Producer Group named Nongstoin PG?",
        ["Is there any Producer Group named Nongstoin PG?"],
        db={"groups_named_like_nongstoin": n},
        raw={"groups_named_like_nongstoin": len({r["pg_id"] for r in R if "nongstoin" in (r["name_of_pg"] or "").lower()})})

    # TC-14: two groups whose name is unique in the DB (one paid once, one paid twice)
    picks = []
    for paid in (1, 2):
        rows = await fetch(f"""SELECT pg_id, MAX(pg_name) n, MAX(no_of_pg_members)::float8 size, SUM(no_of_pg_members)::float8 m
              FROM {V} GROUP BY pg_id HAVING COUNT(*)={paid} AND MAX(no_of_pg_members) BETWEEN 8 AND 20
              ORDER BY md5(pg_id) LIMIT 300""")
        for r in rows:
            nm = r["n"] or ""
            core = nm
            for suf in (" producer group", " pg"):
                if core.lower().endswith(suf):
                    core = core[: -len(suf)]
            core = core.strip()
            if len(core) < 6 or not all(ch == " " or (ch.isascii() and ch.isalpha()) for ch in core):
                continue
            if await one(f"SELECT COUNT(DISTINCT pg_id) FROM {V} WHERE pg_name ILIKE $1", f"%{core}%") != 1:
                continue
            picks.append((r, nm))
            break
    for r, nm in picks:
        rr = [x for x in R if x["pg_id"] == r["pg_id"]]
        add("TC-14", "Check the number of members in a Producer Group", "How many members are there in [pg_name]?",
            [f"How many members are there in {nm}?"],
            db={"pg_id": r["pg_id"], "group_size": r["size"], "memberships_summed": r["m"]},
            raw={"pg_id_rows": len(rr), "group_size": max((x["no_of_pg_members"] for x in rr), default=0),
                 "memberships_summed": sum(x["no_of_pg_members"] for x in rr)},
            extra={"any_of": ["group_size", "memberships_summed"]})

    for n_, m_ in ((5, 15), (10, 20)):
        sizes = await fetch(f"SELECT pg_id, MAX(no_of_pg_members)::float8 size, SUM(no_of_pg_members)::float8 summed FROM {V} GROUP BY 1")
        q_size = sorted([s for s in sizes if s["size"] > m_], key=lambda s: -s["size"])
        q_sum = sorted([s for s in sizes if s["summed"] > m_], key=lambda s: -s["summed"])
        rs = collections.defaultdict(list)
        for x in R:
            rs[x["pg_id"]].append(x["no_of_pg_members"])
        add("TC-15", "Identify Producer Groups based on member count", "List top [number] PGs which has more than [member_number] of members.",
            [f"List top {n_} PGs which has more than {m_} members."],
            db={"groups_size_gt": len(q_size), "top_size": q_size[0]["size"] if q_size else 0,
                "groups_summed_gt": len(q_sum), "top_summed": q_sum[0]["summed"] if q_sum else 0,
                "nth_size": q_size[min(n_, len(q_size)) - 1]["size"] if q_size else 0,
                "sizes": {s["pg_id"]: [s["size"], s["summed"]] for s in sizes}},
            raw={"groups_size_gt": sum(1 for v in rs.values() if max(v) > m_), "top_size": max(max(v) for v in rs.values()),
                 "groups_summed_gt": sum(1 for v in rs.values() if sum(v) > m_), "top_summed": max(sum(v) for v in rs.values())},
            extra={"n": n_, "m": m_})

    add("TC-16", "Calculate the total number of Producer Group members", "What is the total number of PG members recorded till now?",
        ["What is the total number of PG members recorded till now?"],
        db={"members": tot["members"]}, raw={"members": rtot["members"]}, extra={"key": ["members"]})

    d = "WEST GARO HILLS"
    rd = [x for x in R if U(x["mapped_district_lgd_name"]) == d]
    add("TC-17", "Calculate total Producer Group members by district", "What is the total number of PG members in [district]?",
        ["What is the total number of PG members in West Garo Hills?"],
        db={"members": await one(f"SELECT SUM(no_of_pg_members) FROM {V} WHERE lgd_district=$1", d)},
        raw={"members": raw_sum(rd, "no_of_pg_members")}, extra={"key": ["members"]})
    d = "RI BHOI"
    rd = [x for x in R if U(x["mapped_district_lgd_name"]) == d]
    add("TC-18", "Calculate the total amount disbursed by district", "What is the total amount disbursed for [district]?",
        ["What is the total amount disbursed for Ri Bhoi?"],
        db={"amount": await one(f"SELECT SUM(amount_disbursed) FROM {V} WHERE lgd_district=$1", d)},
        raw={"amount": raw_sum(rd, "amount")}, extra={"money": ["amount"]})

    g_sum = await one(f"SELECT COUNT(*) FROM (SELECT pg_id FROM {V} GROUP BY 1 HAVING SUM(amount_disbursed)>100000) x")
    p_one = await one(f"SELECT COUNT(DISTINCT pg_id) FROM {V} WHERE amount_disbursed>100000")
    ra = collections.defaultdict(float)
    for x in R:
        ra[x["pg_id"]] += x["amount"]
    add("TC-19", "Identify Producer Groups based on disbursed amount", "Which Producer Groups received more than ₹[amount]?",
        ["Which Producer Groups received more than ₹1,00,000?"],
        db={"groups_total_gt_1L": g_sum, "groups_single_payment_gt_1L": p_one},
        raw={"groups_total_gt_1L": sum(1 for v in ra.values() if v > 100000),
             "groups_single_payment_gt_1L": len({x["pg_id"] for x in R if x["amount"] > 100000})})

    a, b = dt.date(2025, 4, 1), dt.date(2025, 6, 30)
    r20 = dict((await fetch(f"SELECT COUNT(*)::float8 payments, COUNT(DISTINCT pg_id)::float8 groups, COALESCE(SUM(amount_disbursed),0)::float8 amount "
                            f"FROM {V} WHERE date_of_remittance BETWEEN '2025-04-01' AND '2025-06-30'"))[0])
    rr = [x for x in R if x["date_of_remittance"] and a <= x["date_of_remittance"] <= b]
    by_date = await fetch(f"SELECT date_of_remittance::text d, COUNT(*)::float8 n, SUM(amount_disbursed)::float8 a FROM {V} "
                          "WHERE date_of_remittance BETWEEN '2025-04-01' AND '2025-06-30' GROUP BY 1 ORDER BY 1")
    add("TC-20", "Retrieve remittances within a specific date range", "Show me all remittances made between April and June 2025.",
        ["Show me all remittances made between April and June 2025."],
        db={**r20, "by_date": {x["d"]: [x["n"], x["a"]] for x in by_date}},
        raw={"payments": len(rr), "groups": raw_groups(rr), "amount": raw_sum(rr, "amount")},
        extra={"money": ["amount"], "key": ["payments"]})

    mo = await fetch(f"SELECT TO_CHAR(date_of_remittance,'YYYY-MM') m, SUM(amount_disbursed)::float8 a, COUNT(*)::float8 n FROM {V} "
                     "WHERE financial_year_short='2024-25' GROUP BY 1 ORDER BY 1")
    rm = collections.defaultdict(float)
    for x in R:
        if x["financial_year"] == "2024-25":
            rm[x["date_of_remittance"].strftime("%Y-%m") if x["date_of_remittance"] else "no date"] += x["amount"]
    add("TC-21", "Calculate monthly remittance amounts by financial year", "How much was remitted during each month for financial year [year]?",
        ["How much was remitted during each month for financial year 2024-25?"],
        db={x["m"] or "no date": x["a"] for x in mo}, raw=dict(rm), extra={"money_all": True})

    fy = await fetch(f"SELECT financial_year_short f, COUNT(*)::float8 n FROM {V} GROUP BY 1 ORDER BY 1")
    add("TC-22", "Identify beneficiary records by financial year", "How many records of beneficiaries are available for each financial year?",
        ["How many records of beneficiaries are available for each financial year?"],
        db={x["f"]: x["n"] for x in fy}, raw=dict(collections.Counter(x["financial_year"] for x in R)), extra={"all": True})

    fa = {x["f"]: x["a"] for x in await fetch(f"SELECT financial_year_short f, SUM(amount_disbursed)::float8 a FROM {V} GROUP BY 1")}
    rfa = collections.defaultdict(float)
    for x in R:
        rfa[x["financial_year"]] += x["amount"]
    add("TC-23", "Calculate total remittance for a financial year", "What was the total amount remitted in FY 2024-25?",
        ["What was the total amount remitted in FY 2024-25?"],
        db={"2024-25": fa["2024-25"]}, raw={"2024-25": rfa["2024-25"]}, extra={"money_all": True})
    add("TC-24", "Compare total remittances between financial years", "Compare the total remittance between FY 2023-24 and FY 2024-25.",
        ["Compare the total remittance between FY 2023-24 and FY 2024-25."],
        db={"2023-24": fa.get("2023-24", 0.0), "2024-25": fa["2024-25"]},
        raw={"2023-24": rfa.get("2023-24", 0.0), "2024-25": rfa["2024-25"]}, extra={"money": ["2024-25"], "gap_year": "2023-24"})

    pd_ = await fetch(f"SELECT lgd_district d, COUNT(DISTINCT pg_id)::float8 n FROM {V} GROUP BY 1 ORDER BY 1")
    rpd = collections.defaultdict(set)
    for x in R:
        rpd[U(x["mapped_district_lgd_name"])].add(x["pg_id"])
    add("TC-25", "Count Producer Groups by district", "How many Producer Groups are mapped to each district?",
        ["How many Producer Groups are mapped to each district?"],
        db={x["d"]: x["n"] for x in pd_}, raw={k: len(v) for k, v in rpd.items()}, extra={"all": True})

    d = "WEST KHASI HILLS"
    pb = await fetch(f"SELECT lgd_block b, COUNT(DISTINCT pg_id)::float8 n FROM {V} WHERE lgd_district=$1 GROUP BY 1 ORDER BY 1", [d])
    rpb = collections.defaultdict(set)
    for x in R:
        if U(x["mapped_district_lgd_name"]) == d:
            rpb[U(x["mapped_block_lgd_name"])].add(x["pg_id"])
    add("TC-26", "Count Producer Groups by block within a district", "How many Producer Groups are mapped to each block for [district]?",
        ["How many Producer Groups are mapped to each block for West Khasi Hills?"],
        db={x["b"]: x["n"] for x in pb}, raw={k: len(v) for k, v in rpb.items()}, extra={"all": True})

    vname = "MAWBLAH"
    pv = await fetch(f"SELECT pg_id, MAX(pg_name) n FROM {V} WHERE UPPER(lgd_village_name)=$1 GROUP BY 1 ORDER BY 1", [vname])
    rv = sorted({(x["pg_id"], x["name_of_pg"]) for x in R if U(x["mapped_village_lgd_name"]) == vname})
    add("TC-27", "Identify Producer Groups mapped to a village", "Which Producer Groups are mapped to [village_name] village?",
        ["Which Producer Groups are mapped to Mawblah village?"],
        db={"groups": len(pv), "names": [x["n"] for x in pv], "ids": [x["pg_id"] for x in pv]},
        raw={"groups": len(rv), "names": [x[1] for x in rv], "ids": [x[0] for x in rv]}, extra={"names": True})

    for ac, q in (("Mawkyrwat", "How many Producer Groups are mapped to Mawkyrwat constituency?"),
                  ("Nongstoin", "How many Producer Groups are mapped to Nongstoin?")):
        n = await one(f"SELECT COUNT(DISTINCT pg_id) FROM {V} WHERE UPPER(ac_name)=UPPER($1)", ac)
        rn_ = len({x["pg_id"] for x in R if U(x["mapped_constituency_name"]) == ac.upper()})
        add("TC-28", "Count Producer Groups by constituency", "How many Producer Groups are mapped to [constituency_name]?",
            [q], db={"groups": n}, raw={"groups": rn_}, extra={"key": ["groups"]},
            prefs=[("*", [ac.lower(), "constituency"])])
    return C


async def main():
    async with app_main.lifespan(app_main.app):
        cases = await build_cases()
        only = set(sys.argv[1:])
        if only:
            cases = [c for c in cases if c["tc"] in only]
        sem = asyncio.Semaphore(int(os.environ.get("CONC", "3")))

        async def run(c):
            async with sem:
                t0 = dt.datetime.now()
                c["turns"] = await converse(c["questions"], c["prefs"])
                c["asked_at"] = t0.strftime("%Y-%m-%d %H:%M")
                print("done", c["tc"], c["questions"][-1][:60], flush=True)
        await asyncio.gather(*(run(c) for c in cases))
    out = os.path.join(HERE, os.environ.get("OUT", "fl_sheet_results.json"))
    json.dump(cases, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("written", out, len(cases))


if __name__ == "__main__":
    asyncio.run(main())
