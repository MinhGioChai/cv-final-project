# Project context and handoff

At the start of a work session, read `reports/completion.md` and the latest
linked stage completion report before deciding what to implement. The current
specification is `docs/handoffs/EN_VI_VLM_CODEX_HANDOFF_V3.md`, supplied by the
user on 2026-11-12. Then read `docs/research/RESEARCH_PROTOCOL_V3.md` and
`docs/research/IMPLEMENTATION_PLAN_V3.md`. User instructions take priority.

V3 supersedes V4.2 where they differ: RQ1 and RQ2 are mandatory P0; RQ3
paraphrase and RQ4 visual evidence are conditional P1; separate negation
experiments are P2 future work. Do not promote optional work to P0. V3 section
20 requests audit/planning first and confirmation before major implementation
changes or large inference; honor any later explicit user authorization.

Legacy V4.2 source documents are preserved under `docs/archive/v42/`, with
root compatibility pointers. Old stage reports and Word v1 documents retain
their historical scope; do not rewrite them as if they used V3. Do not restart
Stage 0 or rename runtime schemas/paths just to match the illustrative V3 tree.

The user explicitly wants completion reports retained and updated across
versions so future sessions preserve context. After meaningful work:

`reports/completion.md` is the concise current state. Versions v1–v21 are
preserved byte-for-byte in `reports/completion_history.md`; do not copy that
entire history back into the current entry point. Team setup and Git/data
boundaries are in `HUONG_DAN_NHOM.md`; `CONTRIBUTING.md` redirects there.
Common commands stay in `scripts/`, reconstruction scripts in `scripts/data/`,
and historical Word builders in `scripts/legacy/`. Historical reports retain
their original paths; consult the maintenance move map when tracing them.
Generated review HTML, raw data and
environments stay local or in the private team ZIP, not Git.

Main review now uses v2 (user decision 2026-11-21): A checks both translation
and image/label, then B checks both in the same JSON. Both distinct IDs are
required for both gates; A alone is insufficient. See docs/research/MAIN_REVIEW_V2.md.
Keep v1 backend/template/packets and the two previous ZIPs unchanged; v1 CLI
requires --version v1. Current pages are reports/stage1/v12/main_review/ and
the private review-only archive is exports/main_review_v2.zip.

- Update `reports/completion.md` with current verified state, decisions,
  outstanding work, and a concrete next action; append a dated version entry.
- Keep previous stage reports and evidence. Add a completion report under
  `reports/stageN/` when a new stage completes. Record corrections explicitly.
- Distinguish implemented/tested/QA-approved/real inference from planned or
  synthetic work. Do not carry old test results forward as a new test run.
- Update README when commands or user-facing workflow change.

The current work is a zero-shot paired EN–VI benchmark, not model training.
Preserve source labels, real human review status, pilot/final image exclusions,
and the staged scope described in the handoff. Do not assign individual members.

The user explicitly requested a reminder about the pending Gemma pilot in
future work sessions. When resuming this project, briefly remind them of the
Gemma pilot checklist in `reports/completion.md` until completion is recorded
with real evidence. Respect their current preference to prioritize evaluation.
