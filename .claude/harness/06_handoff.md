# 06 — Handoff Letter to Future Sessions(給未來 Session 的交接信)

> 繁中導讀:三件使用者沒問、但對這個環境最要命的事,加上這套制度最可能的
> 腐化方式與預防法。給每個新 session 的第一封信。

Written 2026-07-06 by the Fable 5 session that built this harness.

---

## Three things nobody asked, but you must know

### 1. Push access is the single point of failure — test it FIRST
The day this harness was built, `git push` returned 403 all session (the
GitHub integration was read-only) while every read worked fine. If that
happens to you, **everything you build is at risk of evaporating** with the
container. Protocol: make your first checkpoint commit early and push it
immediately. If the push 403s, tell the user in that same turn — they must
re-grant write access on the GitHub integration (claude.ai GitHub app / repo
settings); you cannot fix it from inside the container. Do not build for two
hours on top of an unpushable tree.

### 2. The sample-bill round-trip is the only regression test — run it
There is no test suite. The de-facto test is:
`cd hospital_bill_parser && python make_sample_bill.py` then parse the
generated PDF and check the xlsx (2 sheets, date column, 11 categories).
Run this BEFORE touching `parser.py` (baseline) and AFTER (compare). If you
change parser behavior and this round-trip was never run, you have verified
nothing. Converting this into a real pytest file would be worth proposing to
the user (Tier B — it changes workflow).

### 3. The .exe claim is permanently unverifiable from here
`build_app.py` bundles Tesseract into a one-file .exe for the user's
colleagues. This container has no Windows, no display, and no way to test
it. Whatever you change in `build_app.py` or `app.py`, label the Windows
behavior `UNVERIFIED` and ask the user to test on a real machine. A session
that claims "the .exe works" is fabricating.

## How this system will rot, and the countermeasures

| Rot mode | What it looks like | Countermeasure |
|---|---|---|
| **Rule inflation** | Every session appends "one more rule"; CLAUDE.md swells; weak models skim and miss the iron rules | New rules go in harness files, never CLAUDE.md (Tier B anyway). lessons.md compaction at 120 lines. If CLAUDE.md exceeds ~80 lines, that's a Tier B restructuring conversation. |
| **Checkbox theater** | Reports quote the DONE checklist with green ticks but nobody ran the commands | Evidence rule (03 §2): every tick must carry pasted command output. A report whose "evidence" contains no pasted output is auto-FAIL. User spot-check: occasionally reply "paste the read-back" — theater collapses instantly. |
| **Fake isolated verification** | The "fresh" verifier is fed the implementer's summary and rubber-stamps it | 02 Rule 4: verifier gets criteria + file paths ONLY. If a verifier report paraphrases the implementer's wording, re-dispatch. |
| **Settled Facts drift** | User changes things outside Claude; the list goes stale; sessions "protect" features that no longer exist | Reality wins. When observed code contradicts a Settled Fact, update the list (Tier A, with evidence) instead of "restoring" the code. |
| **Threshold erosion** | A stuck model "clarifies" the 2-strike rule into a 5-strike rule mid-failure | Thresholds are Tier B, full stop. A model editing thresholds while failing a task is the anti-gaming clause (05 §4) firing — stop and ask. |

## Status at handoff

Built this session: CLAUDE.md + harness files 01–06 + lessons.md.
Adversarial review + read-back: see final session summary. Push was blocked
by the 403 wall at build time; if you are reading this file from `origin`,
the wall was later lifted and the DONE protocol completed. If you are
reading it only locally, finish the job: push, read back, then report.
