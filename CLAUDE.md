# CLAUDE.md — Task1

> 繁中導讀:本檔是路由中心,只放鐵律、專案事實與檔案指路。細節規則在
> `.claude/harness/`。改本檔前先讀 `.claude/harness/05_maintenance.md`。

## What this repo is

Personal utility repo, Python 3, two independent tools:

- `hospital_bill_parser/` — PDF hospital bills → categorized Excel.
  `parser.py` (core, ~1000 lines: extraction, OCR fallback via pytesseract,
  UB-04 categorization, Excel writer), `app.py` (tkinter GUI),
  `build_app.py` (PyInstaller one-file build, bundles Tesseract),
  `make_sample_bill.py` (test-data generator).
- `organize_photos.py` — sorts photos into date folders.

No test suite. No CI. Runtime deps in `hospital_bill_parser/requirements.txt`.

## Iron rules (non-negotiable, apply to every session)

1. **DONE = pushed + read-back.** Work only counts as finished when the commit
   exists on `origin` and the file has been read back from the remote.
   Sessions run in ephemeral containers: unpushed files are destroyed.
   Full protocol: `.claude/harness/01_diagnostics.md` pain point #1.
2. **Push per deliverable.** Never accumulate more than one finished
   deliverable unpushed. If push fails with 403, report to the user in the
   same turn; do not silently continue.
3. **Implementer never self-verifies.** Verification of nontrivial work goes
   to a fresh-context subagent. Protocol: `.claude/harness/02_orchestration.md`.
4. **Local-first.** Use Bash git / Read / Grep for this repo; GitHub MCP only
   for what local git cannot do.
5. **Two strikes → escalate, don't loop.** The same operation failing twice
   (counting every variant aimed at the same effect — rewording does not
   reset the count) means stop and follow the ladder in
   `.claude/harness/02_orchestration.md`. Never retry a just-denied call
   verbatim.
6. **Don't touch Settled Facts** (below) unless the user names them in the
   current session.

## Settled Facts (finished features — do not "improve" unasked)

- Parser handles native-text AND scanned (OCR) PDFs.
- Batch splitting: one PDF with multiple hospitalizations → multiple claims.
- Excel output: 2 sheets (Summary + Full Breakdown) with date column.
- 11 UB-04 categories are final per user's earlier sessions.
- .exe build bundles Tesseract (zero-install for colleagues). UNVERIFIED on
  real Windows — only the user can test that; never claim it works.

## File router

| Need | Read |
|---|---|
| Why these rules exist; environment failure modes | `.claude/harness/01_diagnostics.md` |
| Dispatching subagents, model up/downgrade ladder, isolated verification | `.claude/harness/02_orchestration.md` |
| Am I done? Is the direction wrong? Should I stop and ask? | `.claude/harness/03_rubrics.md` |
| Copy-paste subagent dispatch templates | `.claude/harness/04_templates.md` |
| How to update these harness files safely | `.claude/harness/05_maintenance.md` |
| Handoff letter: unasked-for warnings, decay modes | `.claude/harness/06_handoff.md` |
| Accumulated lessons from past sessions (read at session start) | `.claude/harness/lessons.md` |

## Session start checklist

1. This file is auto-loaded. Also read `.claude/harness/lessons.md` (short).
2. Confirm your working branch and that `git ls-remote origin` succeeds.
3. Only load other harness files when their trigger applies (router above).
