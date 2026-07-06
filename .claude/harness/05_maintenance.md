# 05 — Harness Maintenance Protocol(知識迭代與反思協議)

> 繁中導讀:規定未來的(弱)模型怎麼安全地更新這套 harness:哪些可以自己
> 改、哪些要先問使用者、踩坑紀錄怎麼寫、多長要精簡。

---

## §1 — Permission tiers(誰能改什麼)

### Tier A — model may edit autonomously (no user approval needed)
- **Append** L-records to `lessons.md` (format in §2). Append-only; never
  rewrite or delete existing records outside a §3 compaction.
- Fix objectively broken references anywhere in the harness: dead file paths,
  renamed tool names, wrong line numbers. Requirement: the report must show
  before/after and the evidence the old value was wrong (e.g., `ls` output).
- Update the **Settled Facts** list in CLAUDE.md when a user-requested change
  this session made an entry factually outdated (change it to match reality,
  quote the user request that caused it).

### Tier B — user approval required BEFORE editing
- Any Iron Rule in CLAUDE.md (add / remove / weaken / "clarify" in a way that
  changes behavior).
- Escalation thresholds and retry ceilings (02), DONE criteria (03 §2),
  circuit-breaker triggers (03 §3). These numbers are load-bearing: a model
  that finds them inconvenient is exactly the model that must not change them.
- Deleting any harness file or merging files together.
- Restructuring CLAUDE.md beyond the Settled Facts list.

### Always, for ANY harness edit (both tiers)
1. Back up first: `cp <file> <file>.bak` (overwrite any older .bak — one
   generation is enough; commit the .bak alongside the edit).
2. Then edit, then commit + push per Iron Rule 1–2.
3. One edit per commit, message starting `harness:`.

## §2 — L-record format for lessons.md(踩坑紀錄格式)

Append at the END of `lessons.md`, exactly this shape, ≤6 lines total:

```
## L-NNN (YYYY-MM-DD)
CONTEXT: what was being attempted, 1 line.
ERROR: what actually went wrong, verbatim key message, 1-2 lines.
RULE: the reusable instruction a future session should follow, 1-2 lines,
imperative mood. If it contradicts an existing L-record, say which one it
supersedes: "supersedes L-NNN".
```

NNN increments from the last record. Write a record when: (a) an escalation
round was burned, (b) an environment behavior surprised you (tool failure
mode, permission wall), (c) the user corrected a wrong assumption. Do NOT
write records for ordinary successes or generic advice ("test your code") —
that is padding, and padding kills this file.

## §3 — Compaction trigger(精簡與抽象化)

When `lessons.md` exceeds **120 lines** (check with `wc -l` at session start):
1. This is a **Tier B** action — propose to the user first, in one message:
   which records you would merge, which RULE lines you would promote into a
   harness file or CLAUDE.md Iron Rule, which are obsolete.
2. On approval: promote durable rules to the proper harness file, rewrite the
   remainder as fewer, more abstract L-records, keep the highest L-number
   sequence going. Move nothing to CLAUDE.md unless it is genuinely
   session-universal.
3. The pre-compaction file must survive as `lessons.md.bak` in the same commit.

## §4 — Anti-gaming clause(防鑽漏洞)

The measure of a harness edit is: *would this have prevented a past failure,
or does it just make today's task easier to declare done?* If the honest
answer is the latter, the edit is forbidden regardless of tier. When in
doubt, treat as Tier B and ask.
