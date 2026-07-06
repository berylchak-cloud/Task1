# 02 — Orchestration & Model Escalation(模型調度與動態升降級守則)

> 繁中導讀:主對話當指揮官,不下場做粗活;粗活派 subagent。派工必附三件套
> (目標、驗收條件、回報格式)。錯兩次就升級,不准原地重試。實作者不得自我
> 驗收。

**Verified environment facts (2026-07-06):** subagent models available via the
`Agent` tool `model` parameter: `haiku`, `sonnet`, `opus`, `fable`. Agent
types: `general-purpose` (all tools), `Explore` (read-only search), `Plan`
(architecture), `claude-code-guide` (Claude Code questions). If a listed model
is rejected at dispatch time, use the session's own model and note it in your
report.

---

## Rule 1 — The commander does not descend(指揮官不下場)

The main conversation makes decisions and integrates conclusions. It does NOT
burn its own context on bulk work.

Dispatch a subagent when ANY of these thresholds is hit:
- You would read **>3 files** or **>300 total lines** to answer one question
  → `Explore` (search breadth: "quick"/"medium"/"very thorough").
- The task is a self-contained implementation with checkable output
  → `general-purpose`, model `sonnet`.
- You need an implementation plan spanning multiple files
  → `Plan`.

The main conversation receives **conclusions only**: paths, `file:line`,
pass/fail, ≤10-line excerpts. A subagent that returns a wall of code has
violated its report contract — extract what you need, then re-state the
report format in the next dispatch.

## Rule 2 — Dispatch triple(派工三件套)

Every subagent prompt MUST contain all three blocks. Templates with fill-in
slots: `04_templates.md`. A dispatch missing any block is malformed — fix it
before sending, not after the subagent wanders.

1. **GOAL + CONTEXT** — what to achieve, why, which files/branches matter,
   what is already settled (paste the relevant Settled Facts line).
2. **ACCEPTANCE CRITERIA** — objectively checkable conditions. "Works
   correctly" is not a criterion; "running `python make_sample_bill.py &&
   python -c 'from parser import ...'` exits 0 and the xlsx has 2 sheets" is.
3. **REPORT FORMAT** — exactly what to return: paths + line numbers +
   pass/fail per criterion. Long artifacts go to disk; the report carries the
   path, never the content.

## Rule 3 — Escalation ladder(升降級路徑)

| Situation | Action |
|---|---|
| `haiku` subagent: 1 tool-call or syntax error | Re-dispatch same task to `sonnet`. Do not give haiku a second chance. |
| `sonnet` (subagent or main): same subtask fails **2** consecutive times | STOP. Package the full failure trail (every attempted command + verbatim error) and re-dispatch to `opus` or `fable`, or surface to the user if the session model is already top-tier. |
| Strong model solved it and the fix is a repeatable pattern | Write the pattern as a concrete recipe/script, then batch-apply with `sonnet` or `haiku`. Don't pay strong-model prices for repetition. |
| Same subtask has consumed **2 full escalation rounds** | Circuit-break: stop all work on it, report state + failure trail to the user, ask. (Rubric: `03_rubrics.md` §3.) |

"Same subtask fails" means the *goal* keeps failing — including "fixed" one
error and got a new one from the same root cause. Rewording a prompt does not
reset the counter.

## Rule 4 — Isolated verification(驗證不自驗)

The agent (or main conversation) that wrote the code/file may not be the one
that pronounces it correct.

- **Files/docs:** a fresh-context subagent (`Explore` or `general-purpose`,
  model `sonnet`) reads the files back from disk (or from `origin` for the
  DONE check) and checks them against the acceptance criteria it is given —
  give it the criteria, NOT your implementation summary or your claims.
- **Code:** verification = execution. Run the real entry point or tests
  (e.g., `python hospital_bill_parser/make_sample_bill.py` then parse the
  produced PDF and inspect the xlsx). "It imports without error" is smoke,
  not verification.
- **High-stakes or subjective judgment:** dispatch 2 independent subagents
  with the same question and no shared context; if they disagree, escalate
  per Rule 3 instead of picking your favorite.
- The verifier's report must quote **actual observed output** (line contents,
  command output, sheet names). A verification report with no quoted evidence
  is invalid — treat as not verified.

## Rule 5 — Report contract for all subagents(回報合約)

Return ONLY:
1. `PASS` / `FAIL` per acceptance criterion, with one line of quoted evidence each.
2. Paths + line numbers for anything created or changed.
3. Up to 5 lines of caveats / UNVERIFIED items.
Anything longer goes into a file; return the path.
