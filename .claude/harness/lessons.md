# Lessons(踩坑紀錄)

> 繁中導讀:跨 session 的教訓紀錄。只准 append,格式見 05_maintenance.md §2。
> 超過 120 行觸發精簡(Tier B,先問使用者)。

## L-001 (2026-07-06)
CONTEXT: First harness build; pushing skeleton to origin.
ERROR: `git push` → 403 from git proxy while reads worked; GitHub MCP
`create_branch` → "403 Resource not accessible by integration".
RULE: Push capability is not guaranteed. Test push right after the FIRST
checkpoint commit of a session, not at the end. On 403, report to user
immediately (permissions problem — user must re-grant write access); do not
retry more than the standard backoff round.

## L-002 (2026-07-06)
CONTEXT: Writing harness files during a session with repeated MCP
disconnect/reconnect cycles.
ERROR: Write/Bash calls failed with "Tool permission stream closed before
response received" — a transport glitch, not a denial.
RULE: Distinguish transport glitches from denials. "stream closed" = retry
once after the connection cycles (it has always succeeded on retry); an
explicit denial = never retry verbatim.

## L-003 (2026-07-06)
CONTEXT: Resolving the L-001 push-403 wall.
ERROR: (resolution record) Root cause was the Claude GitHub App not being
installed on the repo owner account — session had read-only account auth.
RULE: On push 403, tell the user to install the app at
https://github.com/apps/claude → select the repo → approve Contents
Read & Write. Push works immediately after; no session restart needed.
