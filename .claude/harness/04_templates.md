# 04 — Subagent Dispatch Templates(標準化派工模板)

> 繁中導讀:四種常見任務的派工模板,直接複製、填空、送出。填空欄位用
> `{{...}}` 標示。每份模板都內建三件套(目標/驗收/回報)與 02 的回報合約。

Usage: copy the template into the `Agent` tool's `prompt` parameter. Set
`subagent_type` and `model` as noted per template. Fill every `{{slot}}`;
delete a slot's line only if truly inapplicable. Do not add "be thorough /
high quality" filler — only checkable statements.

---

## T1 — Search & Research(搜尋研究)
`subagent_type: Explore` (read-only). Add breadth keyword: quick / medium / very thorough.

```
GOAL: Answer this question about the repo: {{one-sentence question}}
Breadth: {{quick|medium|very thorough}}.

CONTEXT: Repo root is /home/user/Task1. Relevant area: {{files/dirs, e.g.
hospital_bill_parser/parser.py}}. Already known (do not re-derive):
{{1-3 bullet facts, e.g. "OCR fallback lives in extract_line_items"}}.

ACCEPTANCE CRITERIA:
- Every claim in your answer cites file:line.
- If the answer is "not found", list where you looked (paths + patterns).

REPORT FORMAT (nothing else):
1. ANSWER: ≤5 lines.
2. EVIDENCE: file:line + ≤2-line quote per claim.
3. UNCERTAIN: anything you could not confirm.
```

## T2 — Feature Implementation(功能實作)
`subagent_type: general-purpose`, `model: sonnet`.

```
GOAL: Implement: {{one-sentence feature}}. Motivation: {{why the user wants it}}.

CONTEXT: Work in /home/user/Task1 on branch {{branch}}. Touch ONLY
{{allowed files}}. Settled Facts you must not alter: {{paste relevant lines
from CLAUDE.md}}. Follow existing code style in {{reference file}}.

ACCEPTANCE CRITERIA:
- {{observable behavior 1, with the exact command to demonstrate it}}
- {{observable behavior 2}}
- `python -c "import {{module}}"` exits 0; `grep -n "TODO\|FIXME" {{files}}` is empty.
- git-commit your work with a descriptive message. Do NOT push.

REPORT FORMAT (nothing else):
1. PASS/FAIL per criterion + one line of quoted command output each.
2. Files changed: path:line-range list.
3. UNVERIFIED / caveats: ≤5 lines. No code blocks over 10 lines.
```

## T3 — Refactoring(代碼重構)
`subagent_type: general-purpose`, `model: sonnet`. Behavior must not change.

```
GOAL: Refactor {{target}} to {{structural goal, e.g. "extract the 3 duplicate
date-parsing blocks in parser.py into one helper"}}. NO behavior change.

CONTEXT: /home/user/Task1, branch {{branch}}. Baseline behavior snapshot —
BEFORE touching code, run: {{command producing observable output, e.g.
"python hospital_bill_parser/make_sample_bill.py && python -c '...print
sheet names + row counts...'"}} and save output to
{{scratch path}}/baseline.txt.

ACCEPTANCE CRITERIA:
- Same snapshot command after refactor produces byte-identical output
  (diff against baseline.txt is empty).
- Net line count of {{target}} decreases or stays equal.
- No public function signatures changed (list them if you must break this).

REPORT FORMAT: PASS/FAIL per criterion with quoted diff/wc output; files
changed path:lines; caveats ≤5 lines.
```

## T4 — Code / Security Review(代碼與安全審查)
`subagent_type: general-purpose`, `model: sonnet`. Reviewer must be
fresh-context: give it the diff location, NOT your opinions of the code.

```
GOAL: Review {{diff or files}} for defects. You have no prior context on this
change — form your own view from the code only.

CONTEXT: /home/user/Task1. The change claims to: {{1-line claim}}. Get the
diff with: git diff {{base}}..{{head}} -- {{paths}}.

ACCEPTANCE CRITERIA (what counts as a finding):
- Correctness: input/state where behavior is wrong — give the concrete input.
- Data safety: file overwrite/delete paths, silent exception swallowing.
- Security: path traversal from user-supplied filenames, command injection.
- NOT findings: style taste, "could be cleaner", missing type hints.

REPORT FORMAT (nothing else):
1. VERDICT: APPROVE / REQUEST-CHANGES.
2. Findings, most severe first: file:line, 1-sentence defect,
   1-sentence failure scenario. Max 10.
3. If zero findings, state the 3 riskiest spots you checked and why they hold.
```

---

**Verification dispatch** (after T2/T3): use T4's frame but with the
implementer's ACCEPTANCE CRITERIA pasted in as the checklist, per 02 Rule 4.
Never paste the implementer's self-report into the verifier's prompt.
