"""Build the Focus Legacy use-case report: proof PNGs + Excel workbook.
Inputs (beside this file): fl_sheet_results.json (runner), fl_verdicts.json (reviewed verdicts).
Usage (repo root): python fl_write.py <xlsx out> <proof dir>"""
import json
import os
import sys
import textwrap

from PIL import Image, ImageDraw, ImageFont
import openpyxl
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

HERE = os.path.dirname(os.path.abspath(__file__))
XLSX, PROOFS = sys.argv[1], sys.argv[2]
os.makedirs(PROOFS, exist_ok=True)
CASES = json.load(open(os.path.join(HERE, "fl_sheet_results.json"), encoding="utf-8"))
VER = json.load(open(os.path.join(HERE, "fl_verdicts.json"), encoding="utf-8"))
META = VER["meta"]

F = "C:/Windows/Fonts/"
f_h = ImageFont.truetype(F + "segoeuib.ttf", 22)
f_b = ImageFont.truetype(F + "segoeuib.ttf", 16)
f_t = ImageFont.truetype(F + "segoeui.ttf", 15)
f_m = ImageFont.truetype(F + "consola.ttf", 13)
W = 1300
HIDE = ("account", "ifsc", "holder", "branch")


def wrap(draw, text, font, width):
    out = []
    for para in str(text).split("\n"):
        if not para:
            out.append("")
            continue
        line = ""
        for word in para.split(" "):
            cand = (line + " " + word) if line else word
            if draw.textlength(cand, font=font) <= width:
                line = cand
            else:
                if line:
                    out.append(line)
                while draw.textlength(word, font=font) > width:  # very long token (SQL)
                    k = len(word)
                    while k > 1 and draw.textlength(word[:k], font=font) > width:
                        k -= 1
                    out.append(word[:k])
                    word = word[k:]
                line = word
        out.append(line)
    return out


def card(path, title, status, sections):
    colour = {"PASSED": (27, 128, 62), "FAILED": (192, 40, 40), "PASSED WITH OBSERVATION": (196, 120, 0)}.get(status, (90, 90, 90))
    fills = {"q": (237, 241, 252), "bot": (244, 244, 244), "pick": (237, 241, 252), "sql": (250, 250, 250),
             "db": (237, 248, 238), "raw": (255, 247, 230), "v": (255, 255, 255)}
    tmp = Image.new("RGB", (W, 10))
    d0 = ImageDraw.Draw(tmp)
    blocks = []
    for kind, head, body, mono in sections:
        font = f_m if mono else f_t
        lines = wrap(d0, body, font, W - 80)
        if len(lines) > 45:
            lines = lines[:45] + ["… (truncated; full text in the Question Results sheet)"]
        lh = 18 if mono else 22
        blocks.append((kind, head, lines, font, lh, 20 + 26 + lh * len(lines)))
    H = 60 + sum(b[5] + 10 for b in blocks) + 20
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 58], fill=colour)
    d.text((20, 14), f"{title}  ·  {status}", font=f_h, fill="white")
    y = 70
    for kind, head, lines, font, lh, h in blocks:
        d.rectangle([20, y, W - 20, y + h], fill=fills.get(kind, (255, 255, 255)), outline=(205, 205, 205))
        d.text((30, y + 8), head, font=f_b, fill=(40, 40, 40))
        ty = y + 34
        for ln in lines:
            d.text((30, ty), ln, font=font, fill=(30, 30, 30))
            ty += lh
        y += h + 10
    im.save(path)


def fmt(v):
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if isinstance(v, int):
        s = str(abs(v))
        if len(s) > 3:  # Indian grouping
            head, tail = s[:-3], s[-3:]
            parts = []
            while len(head) > 2:
                parts.insert(0, head[-2:])
                head = head[:-2]
            if head:
                parts.insert(0, head)
            s = ",".join(parts) + "," + tail
        return ("-" if v < 0 else "") + s
    if isinstance(v, float):
        return f"{v:,.2f}"
    return str(v)


def figs(d):
    out = []
    for k, v in (d or {}).items():
        if k in ("sizes",):
            continue
        if isinstance(v, dict):
            v = "; ".join(f"{a}: {fmt(b) if not isinstance(b, list) else ' / '.join(fmt(x) for x in b)}" for a, b in v.items())
        elif isinstance(v, list):
            v = ", ".join(fmt(x) for x in v)
        else:
            v = fmt(v)
        out.append(f"{k}: {v}")
    return "\n".join(out)


def safe_rows(rows, total, n=12):
    lines = []
    for r in (rows or [])[:n]:
        lines.append(" | ".join(f"{k}={fmt(v) if isinstance(v, (int, float)) else v}" for k, v in r.items()
                                if not any(h in k.lower() for h in HIDE)))
    total = max(total or 0, len(rows or []))
    if total > n:
        lines.append(f"… {total - n} more row(s) returned")
    return "\n".join(lines)


# ── questions ──────────────────────────────────────────────────────────────
QROWS = []
qn = 0
for ci, c in enumerate(CASES):
    for qi, chain in enumerate(c["turns"]):
        qn += 1
        v = VER["q"][f"{ci}:{qi}"]
        tcl = c["tc"] if "+" not in c["tc"] else (c["tc"].split("+")[0] if qi == 0 else "TC-" + c["tc"].split("+")[1])
        final = chain[-1]
        convo = []
        for t in chain:
            if t["kind"] == "pause":
                convo.append(("bot", "Bot clarification (pause)", f"{t['answer']}\nOptions: " + " | ".join(t.get("options") or []), False))
                convo.append(("pick", "User picked option", t.get("picked") or "", False))
        ans = final.get("answer") or ""
        st = v["status"].upper()
        secs = [("q", f"Question asked (live pipeline, LangGraph, in-process, {c.get('asked_at')})", chain[0]["q"], False)]
        if qi and c["questions"][:qi]:
            secs[0] = ("q", f"Question asked as a follow-up in the same conversation (live pipeline, {c.get('asked_at')})",
                       "Earlier turn: " + c["questions"][qi - 1] + "\nThis turn: " + chain[0]["q"], False)
        secs += convo
        secs.append(("bot", "Bot answer", ans if final["kind"] != "error" else "ERROR: " + ans, False))
        if final.get("rows") and c["kind"] != "knowledge":
            secs.append(("sql", f"Bot result table ({final.get('n_rows')} row(s); first rows)", safe_rows(final["rows"], final.get("n_rows")), True))
        if final.get("sql"):
            secs.append(("sql", "SQL the bot ran", " ".join(final["sql"].split()), True))
        if c["kind"] == "knowledge":
            secs.append(("db", "Reference check — data/incoming/focus_legacy/FOCUS_legacy_Complete_Reference.md", v.get("db_fig", ""), False))
        else:
            secs.append(("db", "Independent DB check — curated.v_focus_legacy (megh_db, live, read-only)", v.get("db_fig") or figs(c["db"]), True))
            secs.append(("raw", "Raw file — Focus Legacy to share to BLH.xlsx (aggregates only)", v.get("raw_fig") or figs(c["raw"]), True))
        secs.append(("v", "Verdict reason", v["reason"], False))
        png = f"{tcl}_Q{qn:02d}.png"
        card(os.path.join(PROOFS, png), f"FOCUS LEGACY {tcl}  ·  Q{qn}", st, secs)
        pauses = [f"[Bot first asked: {t['answer']} -> picked: {t.get('picked')}]" for t in chain if t["kind"] == "pause"]
        QROWS.append(dict(n=qn, ci=ci, tc=tcl, q=chain[0]["q"], ans=("\n".join(pauses) + "\n" if pauses else "") + ans,
                          bot=v.get("bot_fig", ""), db=v.get("db_fig") or figs(c["db"]),
                          raw=v.get("raw_fig") or figs(c["raw"]) if c["kind"] != "knowledge" else "n/a (knowledge question)",
                          bvd=v.get("bot_vs_db", ""), dvr=v.get("db_vs_raw", ""), status=v["status"], reason=v["reason"], png=png))

# ── workbook ───────────────────────────────────────────────────────────────
wb = openpyxl.Workbook()
thin = Side(style="thin", color="BBBBBB")
B = Border(left=thin, right=thin, top=thin, bottom=thin)
HF = PatternFill("solid", fgColor="1F4E78")
PF = {"Passed": PatternFill("solid", fgColor="C6EFCE"), "Failed": PatternFill("solid", fgColor="FFC7CE"),
      "Passed with observation": PatternFill("solid", fgColor="FFEB9C")}
WR = Alignment(wrap_text=True, vertical="top")


def header(ws, cols, widths):
    ws.append(cols)
    for i, c in enumerate(ws[ws.max_row], 1):
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = HF
        c.alignment = Alignment(wrap_text=True, vertical="center")
        c.border = B
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = widths[i - 1]
    ws.freeze_panes = ws.cell(row=ws.max_row + 1, column=2)


# Test cases: one row per use case (TC-11+12 split back into two sheet rows)
TCROWS = []
for t in VER["tc"]:
    TCROWS.append(t)
n_pass = sum(1 for t in TCROWS if t["status"] == "Passed")
n_obs = sum(1 for t in TCROWS if t["status"] == "Passed with observation")
n_fail = sum(1 for t in TCROWS if t["status"] == "Failed")
q_pass = sum(1 for q in QROWS if q["status"] != "Failed")

ws = wb.active
ws.title = "Summary"
ws.column_dimensions["A"].width = 34
ws.column_dimensions["B"].width = 120
ws["A1"] = "Focus Legacy (FOCUS) — Use Case Test Report (TC-01 … TC-28)"
ws["A1"].font = Font(bold=True, size=16)
rows = [("Run date", META["run_date"]),
        ("System under test", "Megh One AI — pipeline.answer_question (LangGraph orchestrator), in-process, live models on the "
                              "vLLM gateway + live megh_db; same code path as POST /api/query"),
        ("Use-case file", "Use_Cases_-_Focus.csv (28 use cases)"),
        ("Database checked", "megh_db, view curated.v_focus_legacy (read-only queries written independently of the bot)"),
        ("Raw data checked", "Focus Legacy to share to BLH.xlsx (14,569 rows). Contains bank account numbers and holder names: "
                             "those columns were never read; only counts and totals were computed."),
        ("Placeholders", "Template placeholders ([pg_name], [district], [amount], [year], [village_name], [constituency_name], "
                         "[number], [member_number]) were filled with real values from the data; the values used are in each row."),
        ("How a case is judged", "PASSED = every figure in the bot's answer equals the independent DB figure, the DB equals the raw file "
                                 "(or the difference is explained), and the answer reads correctly. Knowledge questions are judged "
                                 "against the scheme reference document. PASSED WITH OBSERVATION = figures right, but something in the "
                                 "answer or the data needs attention. FAILED = a wrong / missing figure or a wrong answer."),
        ("", ""),
        ("Use cases tested", len(TCROWS)),
        ("Passed", n_pass),
        ("Passed with observation", n_obs),
        ("Failed", n_fail),
        ("Pass rate (passed + observation)", f"{(n_pass + n_obs) / len(TCROWS):.0%}"),
        ("Questions asked", len(QROWS)),
        ("Questions passed (incl. observation)", f"{q_pass} / {len(QROWS)}"),
        ("", ""),
        ("Statewide totals — DB vs raw", META["totals"]),
        ("DB vs raw — overall", META["db_vs_raw"]),
        ("", ""),
        ("Failed / observations", META["issues"]),
        ("Proof images", META["proof_dir"])]
for i, (a, b) in enumerate(rows, start=3):
    ws.cell(row=i, column=1, value=a).font = Font(bold=True)
    c = ws.cell(row=i, column=2, value=b)
    c.alignment = WR
    if a in ("Passed", "Failed", "Passed with observation"):
        c.fill = PF[a]

ws = wb.create_sheet("Test Case Results")
header(ws, ["TC ID", "Use case", "Example bot query (sheet)", "Question(s) asked today", "Status", "Reason (if failed) / observation",
            "Bot vs DB", "DB vs Raw file", "Proof(s)"], [11, 30, 42, 52, 14, 70, 26, 40, 14])
for t in TCROWS:
    ws.append([t["tc"], t["scenario"], t["template"], t["asked"], t["status"], t["reason"], t["bot_vs_db"], t["db_vs_raw"], t["proofs"]])
    for c in ws[ws.max_row]:
        c.alignment = WR
        c.border = B
    ws.cell(row=ws.max_row, column=5).fill = PF[t["status"]]

ws = wb.create_sheet("Question Results")
header(ws, ["#", "TC ID", "Question asked", "Bot answer (final)", "Bot figure(s)", "DB figure(s) (live megh_db)",
            "Raw file figure(s)", "Bot vs DB", "DB vs Raw", "Status", "Reason / observation", "Proof"],
       [5, 10, 40, 80, 28, 36, 36, 14, 30, 14, 60, 16])
proof_row = {}
for q in QROWS:
    ws.append([q["n"], q["tc"], q["q"], q["ans"][:32000], q["bot"], q["db"], q["raw"], q["bvd"], q["dvr"], q["status"], q["reason"],
               f"Proof Q{q['n']:02d}"])
    for c in ws[ws.max_row]:
        c.alignment = WR
        c.border = B
    ws.cell(row=ws.max_row, column=10).fill = PF[q["status"]]
    ws.row_dimensions[ws.max_row].height = 150

wp = wb.create_sheet("Proofs")
wp.column_dimensions["A"].width = 190
r = 1
for q in QROWS:
    wp.cell(row=r, column=1, value=f"{q['tc']} · Q{q['n']:02d} · {q['status']} · {q['q']}").font = Font(bold=True, size=12)
    proof_row[q["n"]] = r
    img = XLImage(os.path.join(PROOFS, q["png"]))
    scale = 0.75
    img.width, img.height = img.width * scale, img.height * scale
    wp.add_image(img, f"A{r + 1}")
    r += int(img.height / 20) + 4
qs = wb["Question Results"]
for i, q in enumerate(QROWS, start=2):
    c = qs.cell(row=i, column=12)
    c.hyperlink = f"#Proofs!A{proof_row[q['n']]}"
    c.font = Font(color="0563C1", underline="single")

wd = wb.create_sheet("DB vs Raw")
header(wd, ["Check", "DB (curated.v_focus_legacy)", "Raw file", "Result"], [46, 30, 30, 70])
for row in META["dbraw_rows"]:
    wd.append(row)
    for c in wd[wd.max_row]:
        c.alignment = WR
        c.border = B
wb.save(XLSX)
print("saved", XLSX, "questions", len(QROWS), "cases", len(TCROWS), n_pass, n_obs, n_fail)
