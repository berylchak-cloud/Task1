# 01 — Harness Leak Diagnostics(Harness 漏水診斷書)

> 繁中導讀:這份文件記錄本環境最容易讓弱模型翻車的三個物理痛點,以及對應的
> 阻斷方案。所有其他 harness 檔案的規則都源自這三條診斷。規則本體為英文。

**Audience:** every future Claude session in this repo, especially Sonnet/Haiku.
**Status:** written 2026-07-06 by a Fable 5 session. Update via rules in `05_maintenance.md`.

---

## Environment facts (verified, not assumed)

- Sessions usually run on **claude.ai/code web** → an **ephemeral container**.
  The repo is cloned fresh at session start; the container is destroyed after
  the session. **Any file not pushed to the remote is permanently lost.**
- Git remote goes through a local proxy. Reads (fetch/ls-remote) can succeed
  while **pushes return 403** when the GitHub integration lacks write access.
  The GitHub MCP write tools fail the same way ("Resource not accessible by
  integration"). This actually happened on 2026-07-06 — see `lessons.md` L-001.
- The GitHub MCP server **disconnects and reconnects mid-session** (observed
  2026-07-06). Tools vanish and reappear without warning.
- There is **no cross-session memory** except files committed to this repo.
  CLAUDE.md and `.claude/` are the only things a future session automatically
  sees.

---

## Pain point #1 — Phantom completion (假性完成)

**Failure mode:** the model writes files, honestly reports "done", the session
ends, the container is reclaimed, the files never existed as far as the user
is concerned. On this environment this is *not* a hallucination risk — it is
the **default outcome** of any un-pushed work. A second variant: the model
*believes* a Write succeeded but the tool errored, and it never re-checked.

**Physical block (mandatory):**
1. "Done" is **defined** as: `git log origin/<branch>` contains the commit
   AND a read-back of the pushed file (via `git show origin/<branch>:<path> | head`
   or MCP `get_file_contents`) returns the expected content. Not before.
2. Commit + push after **every completed deliverable**, not at the end of the
   session. Maximum unpushed work at any time: one deliverable.
3. If push fails with a **network error**: retry with backoff (2s/4s/8s/16s).
   If it fails with **403**: that is permissions, not network — do NOT retry;
   **tell the user immediately in the same turn**, quoting the exact error
   (only the user can re-grant write access). Either way, never build more
   than the current deliverable on top of an unpushable tree.
4. Never report completion with the words "done/completed/寫入完成" unless
   step 1 passed. If only local commits exist, say exactly:
   "committed locally, NOT pushed — will be lost when this session ends."

---

## Pain point #2 — Context flooding → tool-call decay (工具調用崩潰)

**Failure mode:** the model reads whole large files (`parser.py` is 1,023
lines), pastes big code blocks into chat, and lets MCP tool results pile up.
As context fills, weak models start mis-typing MCP parameters, calling tools
that disconnected, or retrying the same failing call in a loop.

**Physical block (mandatory):**
1. **Local-first rule:** for anything in THIS repo, use `Bash` git + `Read`/
   `Grep`/`Glob`. GitHub MCP tools are only for things local git cannot do
   (PRs, issues, pushing when the git proxy is broken). Fewer MCP calls =
   fewer decay surfaces.
2. **Read budget (per call):** never `Read` more than ~150 lines at once from
   a file >300 lines; `Grep` first, then read the matched region with
   `offset`/`limit`. (Distinct from the >3-files/>300-total-lines *dispatch*
   trigger in `02_orchestration.md` Rule 1 — that one decides when to hand
   the whole job to a subagent.)
3. **Retry ceiling (two strikes, same as CLAUDE.md Iron Rule 5):** a failing
   operation may be corrected and retried **once**. On the second consecutive
   failure of the same operation — counting every variant aimed at the same
   effect; rewording does not reset the count — STOP and follow the
   escalation ladder in `02_orchestration.md`. Never retry a verbatim call
   that was just denied.
4. Bulk scanning (>3 files or unknown scope) goes to an `Explore` subagent;
   the main conversation receives only `file:line` conclusions
   (see `02_orchestration.md`).

---

## Pain point #3 — Semantic drift / re-derivation (語意迷航)

**Failure mode:** with no memory, every session re-derives what this project
is, sometimes wrongly, then "fixes" code that was already correct and
complete. Long sessions additionally forget earlier decisions and contradict
them.

**Physical block (mandatory):**
1. First action of every session that touches code: read `CLAUDE.md`
   (auto-loaded) and `.claude/harness/lessons.md`. They are short by design.
2. The **Settled Facts** list in CLAUDE.md enumerates finished, working
   features. Do not "improve" anything on that list unless the user asked for
   it by name in the current session.
3. Before editing any file, state (to yourself, one line) which user request
   the edit serves. If you cannot name one, do not make the edit.
4. When a session makes a durable decision (new dependency, changed output
   format, renamed function), append it to `lessons.md` in the L-record
   format (`05_maintenance.md`) before ending the turn.

---

## Honesty clause — hard limits of this harness (誠實條款)

Decomposition + isolated verification can push weak-model output close to
strong-model quality for **mechanical** work: parsing, refactoring, tests,
file plumbing. It **cannot** compensate for:

- **Taste / product judgment** (e.g., "does this Excel layout look
  professional?", "which categories would a hospital biller expect?").
  Standard response: produce 2–3 concrete options with screenshots/samples,
  ask the user to pick. Never silently pick one and call it done.
- **Ambiguous requirements** with ≥2 materially different readings.
  Standard response: circuit-break and ask (rubric in `03_rubrics.md`).
- **Facts you cannot verify from this container** (e.g., whether the .exe
  build works on the user's Windows machine — Tesseract bundling can only be
  fully tested there). Standard response: state the untested boundary
  explicitly in the report; never claim it works.

If unsure, look it up; if you cannot look it up, label it `UNVERIFIED` — do
not fabricate.
