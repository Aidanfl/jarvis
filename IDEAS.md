# JARVIS — Roadmap to Amazing

A grounded, ambitious improvement roadmap for this codebase. Every item references
the actual modules it touches, so this is a plan you can execute, not a wish list.

**Legend** — Effort: 🟢 small (hours) · 🟡 medium (a day or two) · 🔴 large (multi-day).
Impact: ⭐ nice · ⭐⭐ noticeable · ⭐⭐⭐ transformative.

> **The single biggest insight from reading the code:** JARVIS already contains a
> full self-improvement stack — `learning.py` (usage patterns), `evolution.py`
> (template improvement), `ab_testing.py` (A/B prompt versions), `tracking.py`
> (success metrics), `qa.py` (output verification), `templates.py` (task templates),
> `suggestions.py` (proactive follow-ups). But almost all of it is bolted to the
> `[ACTION:BUILD]` / Claude-Code dispatch path, which is currently gated off. **The
> highest-leverage work isn't building new intelligence — it's repurposing the
> intelligence that's already here to serve the everyday assistant, not just code builds.**

---

## 1. Intelligence & Reasoning

- **🟡⭐⭐⭐ Replace the `[ACTION:X]` regex with real tool use.** Today actions are parsed
  from the LLM's text with a regex (`extract_action`, `server.py:811`). That's brittle
  (misformatted tags silently drop) and unsafe (no typed args, no gating). Convert each
  action to an Anthropic **tool** with a typed `input_schema`. Claude calls them
  natively, you get structured args, and you can gate/confirm per-tool (exactly the
  "promote to a dedicated tool" pattern for security boundaries). This also makes the
  BUILD safety gate enforced at the tool boundary instead of via string matching.

- **🟡⭐⭐⭐ Model routing by intent.** Everything runs on Haiku (`generate_response`,
  `server.py`). Add a cheap classifier (or a Haiku pre-pass) that routes *hard*
  questions — multi-step reasoning, research, "compare X and Y", coding help — to
  **Sonnet 4.6 or Opus 4.7 with adaptive thinking**, while casual chat stays on Haiku.
  Best of both: snappy small talk, deep answers when it matters.

- **🟢⭐⭐ Prompt caching.** `generate_response` interpolates the time/weather/calendar
  into the **system prompt every turn**, which invalidates the cache prefix on every
  request. Move the volatile context (time, weather, lookups) into a trailing
  user/`<system-reminder>` message and add a `cache_control` breakpoint after the static
  base. ~90% cheaper input + lower latency on every reply. (Flagged during setup.)

- **🟡⭐⭐ Compound / multi-step requests.** "Check my calendar and email and tell me
  what's urgent" currently hits one fast-action path. Let Claude orchestrate multiple
  lookups (calendar + mail + tasks) in one turn and synthesize across them.

- **🟡⭐⭐ Self-verification for high-stakes answers.** `qa.py` already verifies Claude
  Code output by spawning a checker. Generalize the pattern: for factual/numeric answers,
  optionally double-check before speaking (a quick "are you sure?" pass on Sonnet).

- **🟢⭐⭐ `web_fetch` tool.** Pair the new `web_search` with the `web_fetch_20260209`
  server tool so JARVIS can read a *specific* page the user names ("read me the top
  comment on that Hacker News thread") rather than only searching.

- **🟢⭐ Structured outputs for parsing.** Where JARVIS extracts fields (dates, task
  details, calendar account names), use `output_config.format` JSON schema instead of
  free-text parsing — fewer "I misheard the date" failures.

---

## 2. Memory & Personalization

- **🟡⭐⭐⭐ Semantic memory.** `memory.py` uses SQLite **FTS5 keyword** search (`recall`).
  Add embedding-based recall (store vectors, cosine search) so "what did I say about my
  diet" finds "I'm cutting sugar" even without shared keywords. Keep FTS5 as a fast
  fallback/hybrid.

- **🟡⭐⭐⭐ A living user profile.** Periodically synthesize stored memories into a compact
  **profile** (who Aidan is, preferences, people, projects, routines) and inject *that*
  (cached) instead of raw memory hits. JARVIS feels like it actually knows you.

- **🟡⭐⭐ Episodic memory.** Remember past *conversations*, not just facts. "What did we
  talk about last night?" / "pick up where we left off." Store rolling session summaries
  (the `session_summary` plumbing already exists) keyed by date.

- **🟢⭐⭐ Proactive recall.** Surface relevant memories *before* being asked — if you ask
  about a project, lead with what JARVIS remembers about it.

- **🟢⭐ Memory hygiene.** Dedupe near-identical memories, decay stale ones, and
  consolidate ("you've said you prefer React 4 times → promote to a strong preference").

- **🟢⭐⭐ Wire in `learning.py`.** `UsageLearner` already tracks request patterns but is
  build-centric. Feed its patterns into the live prompt: "you usually check your calendar
  around now" → anticipate.

---

## 3. Voice, Latency & Turn-Taking

- **🔴⭐⭐⭐ Streaming TTS.** `synthesize_speech` (`server.py`) waits for the *entire*
  answer, then synthesizes the whole thing before any audio plays. Fish Audio supports
  streaming — pipe sentence-by-sentence: stream the LLM, chunk on sentence boundaries,
  synthesize+play each chunk while the next generates. Cuts time-to-first-word from
  seconds to ~half a second. The single biggest perceived-speed win.

- **🔴⭐⭐⭐ Barge-in (interrupt while speaking).** Right now the mic is *paused* during
  playback (`main.ts` transitions), so you can't cut JARVIS off mid-sentence. Keep the
  mic hot during playback with **acoustic echo cancellation** (so it doesn't hear itself)
  and stop instantly on "JARVIS, stop" or any new wake phrase. Makes it feel alive.

- **🟡⭐⭐ "Let me check" acknowledgements** for slow ops (web search, calendar cold
  fetch) — a short spoken or tonal ack so the ~10s search delay isn't dead air. (Mind the
  two-clip collision we already fixed — gate the ack so it can't race the answer.)

- **🟡⭐⭐ Stream the LLM** in `generate_response` (`messages.stream`) and start TTS on the
  first complete sentence rather than awaiting `end_turn`.

- **🟢⭐ Endpointing/VAD tuning** in `voice.ts` so it commits transcripts faster after you
  stop talking (snappier turns).

---

## 4. Conversation Quality

- **🟡⭐⭐ Tonal/emotional awareness.** Detect user mood/energy from phrasing and match it
  (terse when you're busy, warmer when you're chatty). Feed a one-word mood hint into the
  prompt.

- **🟢⭐⭐ Better follow-ups & pronouns.** "What about tomorrow?" after a calendar query
  should resolve against the prior turn. The history is there (`conversation_history`) —
  make the fast-action paths context-aware, not just the LLM path.

- **🟡⭐⭐ Server-side compaction** (beta `compact-2026-01-12`) for long sessions so JARVIS
  stays coherent across hours without blowing the context window.

- **🟢⭐ Confirm ambiguous/irreversible commands** before acting ("you said delete — the
  note titled X, correct?").

---

## 5. Proactivity & Anticipation

- **🟡⭐⭐⭐ Daily briefing.** A scheduled morning summary: today's calendar (now real, via
  Google), weather, unread count, open tasks, "here's your day, sir." Push it via the
  existing WebSocket notify path.

- **🟡⭐⭐⭐ Ambient reminders.** Watch the calendar cache for upcoming events → proactively
  speak "your 2pm starts in 10 minutes." JARVIS already has background refresh + a push
  channel; this is wiring, not new infra.

- **🟢⭐⭐ Generalize `suggestions.py`.** It only suggests follow-ups for *web-build*
  projects (favicon/tests/readme heuristics). Make it LLM-driven and domain-general:
  after any task, offer one smart next step.

- **🟢⭐ Run `monitor.py` alongside the server** so JARVIS flags its *own* conversation-
  quality issues (it already watches logs) — a feedback loop for tuning.

---

## 6. Integrations & Actions (macOS and beyond)

- **🔴⭐⭐⭐ Shortcuts.app bridge.** One integration to rule them all: `shortcuts run "<name>"`
  via subprocess lets JARVIS trigger *any* user-defined Shortcut — smart home, HTTP calls,
  multi-app automations — without writing each integration. Massive surface for ~a day of work.

- **🟡⭐⭐ Messages / iMessage** (read recent, send with confirmation), **Reminders**,
  **Music/Spotify** (play, skip, "what's playing"), **Contacts** — all AppleScript,
  same pattern as `calendar_access.py` / `mail_access.py`.

- **🟡⭐⭐ Mail beyond read-only.** Currently intentionally read-only. Add **draft & send
  with explicit confirmation** ("draft a reply to Sam… read it back… send?").

- **🟢⭐ Notes editing.** `notes_access.py` is create + read only — add append/edit.

- **🟢⭐⭐ System control.** Volume, brightness, Do-Not-Disturb / Focus modes, lock screen,
  open apps — quick AppleScript wins.

- **🟢⭐⭐ Clipboard & Finder.** "What's on my clipboard," "summarize the file I just
  copied," "open my downloads."

---

## 7. Web & Knowledge

- **🟡⭐⭐ Re-activate research mode.** `browser.py` (Playwright) already does multi-source
  research + screenshots but needs `playwright install` and isn't wired to a voice intent.
  Hook it to "do deep research on X" → spoken summary + a saved report you can open.

- **🟢⭐⭐ Surface sources in the UI.** The web-search answer drops citations (we kept them
  out of speech). Show them as clickable source cards on the orb page (see §9).

- **🟢⭐ Trusted-domain filtering** (`allowed_domains` on `web_search`) for higher-quality
  answers on topics where you trust specific sites.

---

## 8. Autonomy & the BUILD Path — Done Safely

The build/dispatch stack (`work_mode.py`, `qa.py`, `templates.py`, `ab_testing.py`,
`evolution.py`, `tracking.py`) is powerful but currently gated off (`JARVIS_ENABLE_BUILD`)
because it spawned Claude Code with `--dangerously-skip-permissions`. The goal isn't to
leave it off forever — it's to make it **safe to turn on**. And one piece of this is the
everyday feature you actually want now:

- **🟡⭐⭐⭐ Dictate to an open Claude Code session.** "Hey JARVIS, tell Claude Code to add
  tests" → JARVIS types your instruction straight into the running Claude Code terminal.
  The plumbing already exists and is *not* gated by the BUILD switch: `[ACTION:PROMPT_PROJECT]`
  → `prompt_existing_terminal` (`actions.py`) finds a matching Terminal window and keystrokes
  the prompt via System Events. To make it reliable: grant **Accessibility** to the Terminal
  app (System Events keystroke needs it), add clean intents ("tell Claude to…", "have
  Claude…", "ask Claude Code to…"), target the frontmost Claude window, confirm it landed,
  and optionally read Claude's reply back.
- **✅ (wired now) "Open Claude Code" launches a skip-permissions session.** Saying "open
  Claude Code" / "open a terminal" / "fire up Claude" opens Terminal running
  `claude --dangerously-skip-permissions` (`detect_action_fast` → `handle_open_terminal`).

- **🟡⭐⭐⭐ Gated, audited autonomy.** Re-enable BUILD behind: an explicit spoken
  confirmation ("you want me to build X in ~/Desktop/foo — confirm?"), an **append-only
  audit log** of everything it runs, a constrained working directory, and the existing
  **`qa.py`** agent auto-verifying the result. Turn "scary autonomous" into "supervised
  capable."

- **🟡⭐⭐ Self-improving builds (the dormant loop).** Once gated safely, the
  `templates → ab_testing → tracking → evolution` loop becomes live: JARVIS A/B-tests
  prompt templates, tracks which builds succeed, and evolves better templates over time.
  This machinery already exists — it just needs the gate + a quality signal.

- **🟢⭐ Work-mode UX.** Stream Claude Code progress to the orb, allow "stop," and report
  status by voice instead of opening a Terminal.

---

## 9. UI, Orb & Presence

- **🟡⭐⭐⭐ Live captions + transcript.** Show what JARVIS heard and said on the page.
  Removes the "did it hear me?" anxiety and makes debugging trivial.

- **🟡⭐⭐ Rich cards.** Render calendar, weather, search sources, and images as visual
  cards alongside the voice answer — voice-first, not voice-only.

- **🟢⭐⭐ Distinct orb states.** `orb.ts` reacts to audio; give *searching* / *thinking* /
  *listening* visually distinct looks so you can read its state at a glance.

- **🟡⭐⭐ Always-on presence.** `desktop-overlay/` exists — finish it into a floating orb /
  menu-bar item so JARVIS is one glance away, not a browser tab.

---

## 10. Reliability, Observability & Evals

- **🟡⭐⭐⭐ Run as a service.** A `launchd` agent so the backend + frontend start at login
  and auto-restart on crash. Right now it dies with the terminal that launched it. This is
  the difference between "a demo" and "my assistant."

- **🟡⭐⭐ Eval harness.** A fixture of ~50 voice commands → expected behaviors, run on each
  change. `tracking.py` + `ab_testing.py` already store success metrics — point them at
  *assistant* quality, not just builds, so changes can't silently regress.

- **🟢⭐⭐ Cost/latency/error dashboard.** `track_usage` + the usage log already capture
  tokens/cost; add latency + error rates and a `/api/stats` view.

- **🟢⭐ Graceful degradation.** Friendly spoken fallbacks for each failure mode (TTS down,
  STT down, network down) — partially there; make it consistent.

---

## 11. Security & Privacy

- **🔴⭐⭐⭐ Local speech-to-text.** Web Speech API streams your mic audio to **Google**.
  Swap in on-device Whisper (e.g. `whisper.cpp` / a local model) for privacy *and*
  lower latency *and* offline capability. Big one for a "personal" assistant.

- **🟢⭐⭐ Fully-local wake word.** The current "Hey JARVIS" is transcript-based, so the mic
  is always transcribing. A local audio wake-word engine (Picovoice Porcupine has a
  built-in "Jarvis" model) means nothing leaves the device until you summon it.

- **🟢⭐⭐ Action audit log + confirmations** for anything that sends, deletes, or spends —
  especially before re-enabling autonomy (§8).

- **🟢⭐ Keep it loopback.** Backend is bound to `127.0.0.1` (we set that). If you ever
  expose it, add a token on the WebSocket — anyone who can reach the socket can issue
  commands.

---

## 12. Performance & Cost

- **🟢⭐⭐ Prompt caching** (see §1) — biggest single cost lever.
- **🟡⭐⭐ Model routing** (see §1) — Haiku for chat, escalate only when needed.
- **🟢⭐ Cache/dedupe web searches** so repeated questions don't re-search.
- **🟢⭐ Tune `effort` / token budgets** on the escalated (Sonnet/Opus) calls.

---

## 13. Personality & Polish

- **🟢⭐⭐ Configurable persona.** Voice (Fish voice models via `FISH_VOICE_ID`), verbosity,
  wit level, honorific — expose in the Settings panel. (Web-search answers run a little
  long for voice today; a verbosity dial fixes that.)
- **🟢⭐ Modes.** "Focus mode" (terse, no proactive chatter), "casual," "work."
- **🟡⭐ Multi-language** input + output.

---

## 14. Platform & Reach

- **🔴⭐⭐ Mobile companion** — talk to JARVIS from your phone (README lists this as a wanted
  contribution).
- **🔴⭐ Cross-platform** — the AppleScript layer is macOS-only; a pluggable OS-integration
  interface opens Linux/Windows (also a README contribution area).
- **🟡⭐ Multi-device hand-off** — start on the Mac mini, continue on your phone.

---

## 🎯 If I picked the next 6 (highest leverage × reasonable effort)

1. **Streaming TTS** (§3) — 🔴⭐⭐⭐ — the biggest *felt* improvement; kills latency.
2. **Prompt caching + model routing** (§1) — 🟡⭐⭐⭐ — cheaper *and* smarter answers.
3. **Tool-use instead of regex actions** (§1) — 🟡⭐⭐⭐ — reliability + safe autonomy foundation.
4. **Daily briefing + ambient reminders** (§5) — 🟡⭐⭐⭐ — turns a Q&A bot into an assistant.
5. **Run as a `launchd` service** (§10) — 🟡⭐⭐⭐ — always-on, survives restarts.
6. **Shortcuts.app bridge** (§6) — 🔴⭐⭐⭐ — unlocks hundreds of actions for one integration.

Then the crown jewels for "amazing": **local Whisper STT** (§11), **semantic memory +
user profile** (§2), and **barge-in** (§3).

---

*Generated during setup, grounded in the current codebase (Haiku voice loop + web search,
Google Calendar, FTS5 memory, AppleScript integrations, the gated build/dispatch stack).
Re-evaluate as the architecture evolves.*
