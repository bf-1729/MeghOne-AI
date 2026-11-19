import json, os
S = os.path.dirname(os.path.abspath(__file__))
P, O, F = "Passed", "Passed with observation", "Failed"
REF = ("Reference: FOCUS = Farmers' Collectivization for Upscaling Production and Marketing Systems; farmers organised into "
       "Producer Groups; Rs 5,000 per PG member initial mobilisation fund; grant, not a loan; cheques at events and direct bank "
       "transfer (DBT); value-chain, machinery, market-linkage, transport and aggregation support; urban PGs of 10+ members from "
       "Oct 2022; rollout via C&RD blocks.")
FOC = ("Bot first asked which Focus (Focus Legacy or Focus Plus) - expected by design for a bare 'FOCUS' (CLAUDE.md rule); "
       "Focus Legacy chosen.")
K = "n/a - knowledge question (no figure in DB / raw)"
q = {}


def Q(k, status, reason, bot="", db="", raw="", bvd="", dvr=""):
    q[k] = dict(status=status, reason=reason, bot_fig=bot, db_fig=db, raw_fig=raw, bot_vs_db=bvd, db_vs_raw=dvr)


Q("0:0", P, FOC + " Answer expands the acronym correctly, describes Producer Groups, Rs 5,000/member grant, C&RD block rollout, value-chain support - all as in the reference.", "Rs 5,000 per member", REF, bvd="Matches reference", dvr=K)
Q("1:0", O, FOC + " Opening sentence states the objective correctly (collectivise farmers into PGs, financial + value-chain support). Observation: only ONE bullet follows (priority sectors); the income-raising / doubling-income objective and the marketing objective from the reference are left out - thin for an objective question.", "", REF, bvd="Correct but incomplete", dvr=K)
Q("2:0", P, FOC + " Rural PGs, urban PGs of 10+ members (from Oct 2022), per-member benefit Rs 5,000 - matches the reference.", "10 members; Rs 5,000", REF, bvd="Matches reference", dvr=K)
Q("3:0", O, "No pause ('Producer Groups' pins Focus Legacy). Content matches the reference (collective access unit, block registration, 10-member urban minimum, Rs 5,000/member, value-chain hub). Observation: the answer ends with a dangling 'From the scheme FAQ: 4.' - a broken citation stub shown to the user (new KI-695).", "Rs 5,000; 10 members", REF, bvd="Matches reference", dvr=K)
Q("4:0", O, FOC + " Rs 5,000 per member, grant not loan, seed capital, value-chain support - matches the reference. Observation: ends with a dangling 'From the scheme FAQ: 6.' (KI-695).", "Rs 5,000", REF, bvd="Matches reference", dvr=K)
Q("5:0", P, "No pause. Grant of Rs 5,000/member, value-chain/machinery/market linkage, PG formation, cheque/DBT, C&RD blocks - matches the reference.", "Rs 5,000; 10 members", REF, bvd="Matches reference", dvr=K)
Q("6:0", P, FOC + " Grant of Rs 5,000 per member credited to individual members; cheques at public events earlier, direct bank transfer now - matches the reference.", "Rs 5,000", REF, bvd="Matches reference", dvr=K)
Q("7:0", P, FOC + " Concise briefing: PGs, Rs 5,000 grant, urban extension Oct 2022, value-chain support, DBT/cheques - matches the reference.", "Rs 5,000; 10+ members", REF, bvd="Matches reference", dvr=K)
Q("8:0", P, "Bot 11,906 producer groups = DB COUNT(DISTINCT pg_id) 11,906 = raw distinct pg_id 11,906.", "11,906", "groups: 11,906", "groups: 11,906", "Match", "Match")
Q("9:0", P, FOC + " Bot gives payments 14,569, groups 11,906, memberships 1,02,021, amount Rs 51,01,05,000 - all four equal DB and raw, and it explains memberships are not distinct people.", "14,569 / 11,906 / 1,02,021 / Rs 51,01,05,000", "", "", "Match (4/4)", "Match (4/4)")
Q("10:0", P, "Bot 11,906 unique PGs = DB 11,906 = raw 11,906.", "11,906", "groups: 11,906", "groups: 11,906", "Match", "Match")
Q("10:1", P, "Follow-up in the same conversation, understood correctly. Bot: no duplicate records (no group paid twice on one date); 2,655 groups paid more than once; 2,663 repeat payments (14,569 - 11,906). DB 2,655 / 2,663 = raw 2,655 / 2,663.",
  "2,655 groups; 2,663 repeat payments; 0 duplicate records",
  "groups paid >1 time: 2,655\nextra payments: 2,663\nnames shared by 2+ ids: 856",
  "groups paid >1 time: 2,655\nextra payments: 2,663\nnames shared by 2+ ids: 991", "Match",
  "Match on ids/payments. Name-level counts differ (856 vs 991): 1,634 groups carry more than one name across payments and the DB keeps a different name set for them; ids, members and amounts are identical.")
Q("11:0", P, "Bot: no producer group named 'Nongstoin PG' (matched on words, ignoring PG). DB: 0 groups with 'nongstoin' in the name; raw: 0.", "0 (not found)", "groups named like Nongstoin: 0", "groups named like Nongstoin: 0", "Match", "Match")
Q("12:0", F, "WRONG SCHEME. The PG 'Balmora Piggery' (PG-FOCUS-SGH-12260, 10 members, paid once) was taken as the CM Elevate piggery sub-scheme: the bot asked 'CM Elevate or CM Elevate Legacy?' (no Focus Legacy option offered) and answered '1,353 members ... under Meghalaya Piggery Development Scheme' - that is the CM Elevate Legacy piggery count, not this group. Correct answer: 10 members (DB = raw). Diagnostic re-ask with 'PG' / 'producer group' in the question correctly offers Focus Legacy. New KI-693.",
  "1,353 (CM Elevate Legacy piggery scheme)", "pg_id PG-FOCUS-SGH-12260: group size 10, paid once", "1 row, size 10", "Mismatch (wrong scheme)", "Match")
Q("13:0", P, "Bot: Karni Majeh Producer Group (PG-FOCUS-RB-11049, Jirang, Ri Bhoi) has 14 members; size changed 7 -> 14 over its 2 payments. DB: max size 14, summed 21 over 2 payments; raw identical. Correct use of group size (MAX), not the summed memberships.",
  "14 (largest of 2 recorded sizes: 7, 14)", "group size 14; memberships summed 21; 2 payments", "group size 14; memberships summed 21; 2 rows", "Match", "Match")
Q("14:0", P, "Bot: 1,047 groups have more than 15 members; top 5 led by Nongprat Lynti (190), then groups of 20 (548 payments are at size 20, so any 4 such groups are a correct top 5). DB: 1,047 groups with size > 15, top 190; raw identical.",
  "1,047 groups; top 190, then 20s", "groups size>15: 1,047; top size 190", "groups size>15: 1,047; top size 190", "Match", "Match")
Q("15:0", O, "Figure right: only ONE group has more than 20 members (Nongprat Lynti, 190) - DB 1 = raw 1, so a 'top 10' can only list one. Observation: the answer reads 'the recorded total is 190 group size' and does not say that only 1 of the 10 requested exists (template wording; KI-696).",
  "1 group (190)", "groups size>20: 1; top 190", "groups size>20: 1; top 190", "Match", "Match")
Q("16:0", P, "Bot 1,02,021 PG members (memberships, explained as not distinct people) = DB SUM(no_of_pg_members) 1,02,021 = raw 1,02,021.", "1,02,021", "members: 1,02,021", "members: 1,02,021", "Match", "Match")
Q("17:0", P, "Bot 21,867 PG members in West Garo Hills = DB 21,867 = raw 21,867.", "21,867", "members: 21,867", "members: 21,867", "Match", "Match")
Q("18:0", P, "Question names no scheme, so the bot asked which scheme (fair; Focus Legacy picked). Bot Rs 4,92,90,000 = DB 49,290,000 = raw 49,290,000.", "Rs 4,92,90,000", "amount: Rs 4,92,90,000", "amount: Rs 4,92,90,000", "Match", "Match")
Q("19:0", F, "Headline right: 541 groups received more than Rs 1,00,000 in total (DB 541 = raw 541), and the 25 listed rows are correct. But the 'Key points' state false facts: 'Payments: 50 in total, across 25 districts', 'Every district has 2' - the 25 rows are 25 GROUPS in 10 districts (Meghalaya has 12 districts); '2' is payments per group. Every row also repeats 'groups qualifying: 541'. Same defect as open KI-686 (Key points count rows as districts).",
  "541 groups (correct); '25 districts' (wrong)", "groups with total > Rs 1 lakh: 541\ngroups with one payment > Rs 1 lakh: 1",
  "groups with total > Rs 1 lakh: 541\ngroups with one payment > Rs 1 lakh: 1", "Headline match; summary wrong", "Match")
Q("20:0", F, "Count right: 5,106 remittances between April and June 2025 (DB 5,106 = raw 5,106). But the answer never gives the amount (Rs 9,54,40,000) and lists only the first 1,000 rows, all dated 18-Jun-2025; its key points ('All in 2025-06-18', 'No of pg members: 3,275 in total') describe only those 1,000 rows. Actual: 3 batches - 18 Jun 3,359 / Rs 6.14 cr, 20 Jun 1,041 / Rs 1.56 cr, 26 Jun 706 / Rs 1.84 cr. New KI-694.",
  "5,106 (correct); amount not stated; 'All in 2025-06-18' (misleading)",
  "payments 5,106; groups 5,106; amount Rs 9,54,40,000\n18-Jun: 3,359 / Rs 6,14,20,000\n20-Jun: 1,041 / Rs 1,56,15,000\n26-Jun: 706 / Rs 1,84,05,000",
  "payments 5,106; groups 5,106; amount Rs 9,54,40,000", "Count match; amount missing; summary misleading", "Match")
Q("21:0", P, "FY 2024-25 has a single remittance month: October 2024, Rs 11,49,90,000 (22,998 memberships). DB: only 2024-10 = Rs 114,990,000; raw identical.", "Oct 2024: Rs 11,49,90,000", "2024-10: Rs 11,49,90,000", "2024-10: Rs 11,49,90,000", "Match", "Match")
Q("22:0", P, "Question names no scheme -> scheme asked (fair). Bot 965 / 2,139 / 2,653 / 8,812 for FY 2021-22 / 22-23 / 24-25 / 25-26 = DB = raw. FY 2023-24 correctly absent.", "965; 2,139; 2,653; 8,812", "", "", "Match (4/4)", "Match (4/4)")
Q("23:0", P, "Bot Rs 11,49,90,000 for FY 2024-25 = DB 114,990,000 = raw 114,990,000.", "Rs 11,49,90,000", "", "", "Match", "Match")
Q("24:0", P, "FY 2023-24 holds no Focus Legacy payments (DB 0 rows, raw 0 rows); the bot says so ('a gap, not a zero') and compares the nearest year with data, FY 2022-23 (Rs 14,17,90,000) - by design (_apply_year_gap). FY 2024-25 Rs 11,49,90,000 = DB = raw; 2022-23 figure = DB 141,790,000. Difference Rs 2,68,00,000 correct.",
  "2023-24: no data; 2022-23 Rs 14,17,90,000; 2024-25 Rs 11,49,90,000", "2023-24: none\n2022-23: Rs 14,17,90,000\n2024-25: Rs 11,49,90,000",
  "2023-24: none\n2024-25: Rs 11,49,90,000", "Match", "Match")
Q("25:0", P, "All 12 district counts equal DB and raw (e.g. West Garo Hills 2,701, North Garo Hills 1,173, South West Khasi Hills 440); total 11,906.", "12 districts, total 11,906", "", "", "Match (12/12)", "Match (12/12)")
Q("26:0", P, "All 5 West Khasi Hills blocks equal DB and raw (Nongstoin 460, Mawshynrut 286, Shallang 78, Rambrai 56, Ri Muliang 41), and the bot adds the 5 groups with no block (DB 5 = raw 5) for the district total 926.", "5 blocks + 5 no-block = 926", "", "", "Match (5/5 + no-block)", "Match")
Q("27:0", P, "Bot lists exactly the 4 groups of Mawblah village (Iamonlang, Iabeitlang, Knanlang Pg, Iaryntihlang, with ids) = DB = raw (same ids and names).", "4 groups", "4 groups: Iamonlang, Iabeitlang, Knanlang Pg, Iaryntihlang", "same 4 groups", "Match", "Match")
Q("28:0", P, "Bot 311 PGs in Mawkyrwat constituency = DB 311 (ac_name) = raw 311 (mapped_constituency_name).", "311", "groups: 311", "groups: 311", "Match", "Match")
Q("29:0", O, "Figure right: 268 PGs in Nongstoin constituency = DB 268 = raw 268. Observations: (1) two clarification pauses before the answer - 'district, block or constituency?' (lists 'district' though Nongstoin is not a district) then 'whole constituency or part?'; (2) answer wording is machine-like: 'The query counts 268 ... The result shows 268 for the producer_groups metric' (its first draft misquoted 26,800 and was caught by the faithfulness check). KI-696.",
  "268", "groups: 268", "groups: 268", "Match", "Match")


def tcr(tc, scen, tmpl, asked, status, reason, bvd, dvr, proofs):
    return dict(tc=tc, scenario=scen, template=tmpl, asked=asked, status=status, reason=reason, bot_vs_db=bvd, db_vs_raw=dvr, proofs=proofs)


kn = "n/a (knowledge; judged vs reference doc)"
tc = [
    tcr("TC-01", "Understand the FOCUS scheme", "What is the FOCUS scheme in Meghalaya?", "Q1: same", P, "", "Matches reference", kn, "Q01"),
    tcr("TC-02", "Understand the scheme objective", "What is the main objective of FOCUS?", "Q2: same", O, q["1:0"]["reason"], "Correct but incomplete", kn, "Q02"),
    tcr("TC-03", "Understand beneficiary eligibility", "Who can benefit under the FOCUS scheme?", "Q3: same", P, "", "Matches reference", kn, "Q03"),
    tcr("TC-04", "Understand Producer Groups", "What is the role of Producer Groups under FOCUS?", "Q4: same", O, "Content correct; answer ends with a dangling 'From the scheme FAQ: 4.' (KI-695).", "Matches reference", kn, "Q04"),
    tcr("TC-05", "Understand financial assistance", "What type of financial assistance is provided under FOCUS?", "Q5: same", O, "Content correct; answer ends with a dangling 'From the scheme FAQ: 6.' (KI-695).", "Matches reference", kn, "Q05"),
    tcr("TC-06", "Understand scheme support provided to Producer Groups", "What kind of support does FOCUS provide to Producer Groups?", "Q6: same", P, "", "Matches reference", kn, "Q06"),
    tcr("TC-07", "Understand fund distribution", "How is financial assistance distributed under FOCUS?", "Q7: same", P, "", "Matches reference", kn, "Q07"),
    tcr("TC-08", "Understand scheme coverage", "How many Producer Groups have been covered under FOCUS?", "Q9: same", P, "", "Match (11,906)", "Match", "Q09"),
    tcr("TC-09", "Get a scheme overview for official briefing", "Give me a short overview of FOCUS that I can use for an official briefing.", "Q8: same", P, "", "Matches reference", kn, "Q08"),
    tcr("TC-10", "Identify total beneficiaries", "How many total beneficiaries are available under the FOCUS scheme?", "Q10: same", P, "", "Match (4/4 figures)", "Match", "Q10"),
    tcr("TC-11", "Identify unique Producer Groups", "How many unique Producer Groups are present under FOCUS scheme?", "Q11: same", P, "", "Match (11,906)", "Match", "Q11"),
    tcr("TC-12", "Identify duplicate Producer Groups", "Are there any duplicate Producer Groups there?", "Q12: same, as a follow-up to Q11", P, "", "Match (2,655 / 2,663)", q["10:1"]["db_vs_raw"], "Q12"),
    tcr("TC-13", "Search for a Producer Group by name", "Is there any Producer Group named Nongstoin PG?", "Q13: same", P, "", "Match (none)", "Match", "Q13"),
    tcr("TC-14", "Check the number of members in a Producer Group", "How many members are there in [pg_name]?", "Q14: ... in Balmora Piggery?\nQ15: ... in Karni Majeh Producer Group?", F,
        "Q14 FAILED: a PG named 'Balmora Piggery' was routed to the CM Elevate piggery sub-scheme and answered 1,353 (correct: 10). Q15 passed (14 = DB = raw). KI-693.", "Q14 mismatch; Q15 match", "Match", "Q14, Q15"),
    tcr("TC-15", "Identify Producer Groups based on member count", "List top [number] PGs which has more than [member_number] of members.", "Q16: top 5 ... more than 15\nQ17: top 10 ... more than 20", O,
        "Figures right in both (1,047 groups >15; only 1 group >20). Q17 wording: 'the recorded total is 190 group size', no note that only 1 of 10 exists (KI-696).", "Match", "Match", "Q16, Q17"),
    tcr("TC-16", "Total Producer Group members", "What is the total number of PG members recorded till now?", "Q18: same", P, "", "Match (1,02,021)", "Match", "Q18"),
    tcr("TC-17", "Total PG members by district", "What is the total number of PG members in [district]?", "Q19: ... in West Garo Hills?", P, "", "Match (21,867)", "Match", "Q19"),
    tcr("TC-18", "Total amount disbursed by district", "What is the total amount disbursed for [district]?", "Q20: ... for Ri Bhoi?", P, "", "Match (Rs 4,92,90,000)", "Match", "Q20"),
    tcr("TC-19", "Producer Groups based on disbursed amount", "Which Producer Groups received more than ₹[amount]?", "Q21: ... more than ₹1,00,000?", F, q["19:0"]["reason"], "Headline match; summary wrong", "Match", "Q21"),
    tcr("TC-20", "Remittances within a date range", "Show me all remittances made between April and June 2025.", "Q22: same", F, q["20:0"]["reason"], "Count match; amount missing; summary misleading", "Match", "Q22"),
    tcr("TC-21", "Monthly remittance by financial year", "How much was remitted during each month for financial year [year]?", "Q23: ... financial year 2024-25?", P, "", "Match", "Match", "Q23"),
    tcr("TC-22", "Beneficiary records by financial year", "How many records of beneficiaries are available for each financial year?", "Q24: same", P, "", "Match (4/4)", "Match", "Q24"),
    tcr("TC-23", "Total remittance for a financial year", "What was the total amount remitted in FY 2024-25?", "Q25: same", P, "", "Match", "Match", "Q25"),
    tcr("TC-24", "Compare remittances between financial years", "Compare the total remittance between FY 2023-24 and FY 2024-25.", "Q26: same", P, "FY 2023-24 has no data (DB and raw); bot says so and compares FY 2022-23 instead (by design).", "Match", "Match", "Q26"),
    tcr("TC-25", "Producer Groups by district", "How many Producer Groups are mapped to each district?", "Q27: same", P, "", "Match (12/12)", "Match", "Q27"),
    tcr("TC-26", "Producer Groups by block within a district", "How many Producer Groups are mapped to each block for [district]?", "Q28: ... for West Khasi Hills?", P, "", "Match (5/5 + no-block 5)", "Match", "Q28"),
    tcr("TC-27", "Producer Groups mapped to a village", "Which Producer Groups are mapped to [village_name] village?", "Q29: ... to Mawblah village?", P, "", "Match (4 groups)", "Match", "Q29"),
    tcr("TC-28", "Producer Groups by constituency", "How many Producer Groups are mapped to [constituency_name]?", "Q30: ... to Mawkyrwat constituency?\nQ31: ... to Nongstoin?", O,
        "Figures right (311; 268). Q31: two clarification pauses and machine-like wording ('The query counts ... producer_groups metric') (KI-696).", "Match", "Match", "Q30, Q31"),
]
meta = dict(
    run_date="2026-11-19 (live run, VPN up)",
    totals="DB = raw on every statewide figure: 14,569 payments; 11,906 producer groups; 1,02,021 memberships; Rs 51,01,05,000; FY 2021-22 965 / 2022-23 2,139 / 2024-25 2,653 / 2025-26 8,812 payments (no FY 2023-24 in either).",
    db_vs_raw="Full reconciliation (all 12 districts, 57 blocks, 56 constituency values, 3,382 mapped villages, 31 remittance-date values, 4 FYs, all 11,906 group ids - payments, groups, members, amount): NO difference. The 1,101 payments with no village / constituency read 'NULL' in the raw file and NULL / 'Unresolved' in the DB - the same rows. Only PG NAMES differ for 1,634 groups recorded under more than one name (DB 9,452 distinct names vs raw 10,678); ids and figures are unaffected.",
    issues="FAILED: TC-14 (a PG named '... Piggery' routed to CM Elevate, answered 1,353 instead of 10 - KI-693); TC-19 (key points say '25 districts' / 'every district has 2' - KI-686); TC-20 (no total amount; summary built from the first 1,000 rows only, 'All in 2025-06-18' - KI-694). OBSERVATIONS: TC-02 thin objective answer; TC-04 / TC-05 dangling 'From the scheme FAQ: N.' (KI-695); TC-15 / TC-28 wording + two pauses for Nongstoin (KI-696). No headline figure disagreed with the DB except TC-14 Q14.",
    proof_dir="docs/reports/fl_proofs_2026-11-19/ (one PNG per question; also embedded in the 'Proofs' sheet). Proof cards are rendered from the live run's records (question, pauses, answer, SQL, independent DB and raw figures), not browser screenshots.",
    dbraw_rows=[
        ["Statewide payments / groups / members / amount", "14,569 / 11,906 / 1,02,021 / Rs 51,01,05,000", "14,569 / 11,906 / 1,02,021 / Rs 51,01,05,000", "Identical"],
        ["Financial years (payments)", "2021-22 965; 2022-23 2,139; 2024-25 2,653; 2025-26 8,812", "same", "Identical; FY 2023-24 absent in both"],
        ["12 districts x (payments, groups, members, amount)", "48 figures", "48 figures", "Identical (0 differences)"],
        ["57 block values x 4 measures", "incl. 88 payments with no block", "incl. 88 rows 'NULL'", "Identical (only the empty label differs: NULL vs 'NULL')"],
        ["56 constituency values x 4 measures", "incl. 1,101 payments with no constituency", "incl. 1,101 rows 'NULL'", "Identical (same rows)"],
        ["Villages (district/block/village) payments", "3,382 mapped villages + 1,101 unmapped", "3,382 mapped villages + 1,101 'NULL'", "Identical (0 differences on mapped villages)"],
        ["Remittance dates", "30 dates + 171 with no date", "30 dates + 171 'NULL'", "Identical"],
        ["Per-group payments and members (11,906 ids)", "11,906", "11,906", "Identical (0 differences)"],
        ["PG names", "9,452 distinct", "10,678 distinct", "Differ for 1,634 groups that appear under more than one name across payments; no count or amount changes"],
        ["Privacy", "v_focus_legacy only (masked account; no holder name)", "account_no / name_on_the_account / ifsc / branch never read", "Aggregates only"],
    ])
json.dump(dict(q=q, tc=tc, meta=meta), open(os.path.join(S, "fl_verdicts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(q), len(tc), {s: sum(1 for t in tc if t["status"] == s) for s in (P, O, F)})
