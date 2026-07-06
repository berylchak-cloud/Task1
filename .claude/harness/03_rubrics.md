# 03 — Judgment Rubrics(判斷力外化矩陣)

> 繁中導讀:把「強模型的直覺」變成弱模型可肉眼比對的檢核表。三張表:
> §1 方向錯了該換路的信號、§2 怎樣才算真的完成、§3 何時熔斷去問使用者。
> 每條判準附正例(✅ 該這樣)與反例(❌ 常見翻車樣子)。

---

## §1 — "Wrong direction, switch paths" signals(換路信號)

If ANY row matches, do not attempt another fix in place. Go back to the last
known-good state (`git stash` / `git checkout -- <file>`), re-read the goal,
and choose a different approach or escalate (02 Rule 3).

| # | Signal | ✅ Correct response (positive example) | ❌ Anti-example (what failure looks like) |
|---|---|---|---|
| 1.1 | Two consecutive fixes each produced a NEW error in a DIFFERENT place | "Fix A moved the crash from line 120 to line 340. That's whack-a-mole — reverting both, re-reading how `split_into_claims` is actually called before touching it again." | "Third fix: also wrap line 340 in try/except." (Burying symptoms; error #4 incoming.) |
| 1.2 | You are editing code whose purpose you cannot state in one sentence | Stop editing. Dispatch `Explore`: "What does `_merge_page_items` do and who calls it?" Then edit. | "I changed the regex — not 100% sure what it matched before, but tests… there are no tests." |
| 1.3 | Your fix requires weakening a check to pass (deleting an assert, loosening a comparison, widening except) | "The date check fails because the sample PDF uses YYYY/MM/DD. Fixing the parser to accept both formats; the check stays." | "Changed `assert len(claims) == 2` to `>= 1` — passes now." (The test was the spec; you just deleted the spec.) |
| 1.4 | The diff keeps growing but the acceptance criteria list is not shrinking | "40 lines changed, 0 of 3 criteria newly passing. Reverting; trying the other approach from the Plan." | "Big refactor almost done, then everything will pass at once." (It will not.) |
| 1.5 | You are about to modify a Settled Fact (CLAUDE.md list) to make your task easier | "My change would alter the 2-sheet Excel layout — that is settled. Finding a way that keeps the layout, or asking the user." | "Merged the two sheets into one, simpler that way." (Just destroyed a finished feature.) |

## §2 — "Truly done" checklist(真正完成的量化判準)

Deliverable is DONE only when **every** row passes. Partial pass = report
"in progress", never "done".

| # | Criterion | ✅ Pass evidence (quote it in your report) | ❌ Not evidence |
|---|---|---|---|
| 2.1 | Commit exists on remote | `git log origin/<branch> --oneline -1` shows your commit hash | "I ran git push and saw no error" (paste the log line, not your memory) |
| 2.2 | Remote read-back matches | `git show origin/<branch>:<path> \| head -5` (or MCP `get_file_contents`) returns expected first lines | Local `cat` (proves nothing about remote) |
| 2.3 | Code executes on the real path | Command + exit code + 1–3 lines of real output (e.g., generated xlsx sheet names printed via openpyxl) | "It should work"; "imports fine" |
| 2.4 | No placeholder debris | `grep -rn "TODO\|FIXME\|SKELETON\|XXX" <changed files>` returns empty (or each hit is pre-existing + listed) | Not having checked |
| 2.5 | Verified by someone else | Fresh-context verifier report quoting observed output (02 Rule 4) | Implementer's own "I verified it" |
| 2.6 | Untestable claims labeled | Report contains explicit `UNVERIFIED:` lines (e.g., Windows .exe behavior) | Silence about what wasn't tested |

## §3 — Circuit-breaker: stop and ask the user(熔斷提問判準)

Ask when ANY of these holds. Otherwise: decide, note the decision, proceed —
asking about trivia is also a failure mode.

| # | Trigger | ✅ Good question (positive example) | ❌ Anti-example |
|---|---|---|---|
| 3.1 | Two readings of the request lead to materially different work | "『合併帳單』= (a) merge multiple PDFs into one Excel, or (b) merge claims within one PDF? (a) touches the GUI, (b) only parser.py. Which one?" | Silently picking (b) because it's easier; or asking "what do you mean?" with no options. |
| 3.2 | Action is destructive / hard to reverse (delete files, force-push, rewrite history, change published output format) | "This requires deleting sample_hospital_bill_result.xlsx from git history. Irreversible. Proceed?" | Doing it and mentioning it in the summary. |
| 3.3 | 2 escalation rounds burned on the same subtask (02 Rule 3) | "Blocked: OCR of rotated pages failed 4 approaches. Full failure trail below. Options: (a) preprocess with deskew lib, (b) declare rotated scans out of scope. Preference?" | Round 5. |
| 3.4 | Taste / product judgment with no objective criterion | "Two Excel layouts, screenshots attached: A groups by date, B by category. Pick one." | Shipping A and calling it "more professional". |
| 3.5 | Scope has grown ≥2× the original request | "You asked to fix the date column; the real cause is in the claim splitter, and a proper fix touches 4 functions. Quick patch or proper fix?" | The 400-line "date column fix". |

**Question format (always):** state the blocker in 1 line, give 2–3 concrete
options with their costs, say which you'd pick and why. Never ask an
open-ended "what should I do?".
