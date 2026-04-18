# Priority Task List: `memberful-webhook-inspector`

A local development tool for inspecting and pretty-printing Memberful webhook events as they fire. Built to make it easy to see exactly what Memberful sends, when it sends it, and what changed — the kind of thing a support engineer would want when debugging a customer's integration.

---

## Context for the agent

You are building a small, focused, ship-in-an-hour CLI tool. The author is a senior support / cloud engineer applying for the Customer Happiness Technical Specialist role at Patreon/Memberful. The point of the project is twofold:

1. **Functional**: actually useful for inspecting Memberful webhook payloads during a product trial.
2. **Demonstrative**: shows up in a portfolio repo with a clean README and a clear "I built this while learning your product" story.

Optimize for **clarity, polish, and a tight README** over feature breadth. If a feature isn't needed for the v1 demo, leave it for "Future work" in the README.

Author signature for commits and README: **Daryl Lundy**.

---

## Delivery priorities

Build in priority order. Each task should end in a working state and be committed before starting the next task.

### P0 — runnable secure receiver

The first priority is a minimal local service that can accept Memberful webhook requests safely.

- Create the required project skeleton.
- Add dependency and environment files.
- Load configuration from `.env`.
- Implement signature verification over raw request bytes.
- Expose `POST /webhook` and `GET /health`.
- Reject missing or invalid signatures with `401`.

### P1 — event visibility

The second priority is making webhook traffic easy to inspect during a product trial.

- Pretty-print verified events to the terminal.
- Color-code event names by family.
- Extract useful fields for common Memberful event types.
- Append verified events to `events.jsonl`.
- Append invalid signature attempts to `events.invalid.jsonl`.
- Print a startup banner with the endpoint, log path, and loaded secret status.

### P2 — proof and polish

The final priority is making the repo credible as a portfolio project and easy to run.

- Add focused signature verification tests.
- Write a complete README with quickstart, verification steps, sample output, security notes, future work, and license.
- Confirm manual webhook flows work with signed and unsigned `curl` requests.
- Keep the code small and scoped to the v1 local development tool.

---

## Task list

### Task 1 — project scaffold and runtime contract

**Priority:** P0

**Goal:** Create the smallest project shape needed to run a local FastAPI webhook receiver.

**Deliverables:**

- [ ] `requirements.txt` with only `fastapi`, `uvicorn[standard]`, `rich`, and `python-dotenv`.
- [ ] `.env.example` with `MEMBERFUL_WEBHOOK_SECRET`, optional `PORT`, and optional `LOG_FILE`.
- [ ] `.gitignore` excluding `.env`, `events.jsonl`, `events.invalid.jsonl`, and `__pycache__/`.
- [ ] `inspector/__init__.py`.
- [ ] `inspector/app.py` with app creation, configuration loading, and `GET /health`.
- [ ] Clear startup failure if `MEMBERFUL_WEBHOOK_SECRET` is missing.

**Acceptance checks:**

- [ ] `pip install -r requirements.txt` succeeds.
- [ ] `python -m inspector.app` exits with a clear error when no secret is configured.
- [ ] With a configured secret, the server starts on `PORT` or defaults to `8000`.

**Commit after completion:** `Scaffold webhook inspector project`

### Task 2 — HMAC signature verification

**Priority:** P0

**Goal:** Verify Memberful webhook signatures correctly and defensibly.

**Deliverables:**

- [ ] `inspector/verify.py` with `verify_signature(body: bytes, signature: str, secret: str) -> bool`.
- [ ] HMAC-SHA256 hex digest computed over raw request body bytes.
- [ ] Constant-time comparison with `hmac.compare_digest()`.
- [ ] Missing signatures return `401` with `{"error": "missing signature header"}`.
- [ ] Invalid signatures return `401` with `{"error": "invalid signature"}`.
- [ ] Invalid attempts are visible on stderr with timestamp, source IP, and provided header value.

**Acceptance checks:**

- [ ] Valid signatures are accepted.
- [ ] Missing signatures are rejected before payload handling.
- [ ] Tampered bodies, signatures, and secrets are rejected.

**Commit after completion:** `Add Memberful signature verification`

### Task 3 — webhook endpoint behavior

**Priority:** P0

**Goal:** Complete the receiver behavior for verified JSON webhook requests.

**Deliverables:**

- [ ] `POST /webhook` reads raw request bytes before JSON parsing.
- [ ] Any JSON payload is accepted after signature verification.
- [ ] Verified requests return `200` with `{"status": "ok"}`.
- [ ] Endpoint work stays minimal so responses remain well under Memberful's 15-second retry threshold.

**Acceptance checks:**

- [ ] Signed `curl` POST returns `200`.
- [ ] Unsigned `curl` POST returns `401`.
- [ ] Wrong-signature `curl` POST returns `401`.

**Commit after completion:** `Handle signed webhook requests`

---

## Tech stack

- **Language**: Python 3.11+
- **Framework**: FastAPI + Uvicorn
- **Dependencies**: `fastapi`, `uvicorn[standard]`, `rich` (for pretty terminal output), `python-dotenv` (for loading the signing secret)
- **No other dependencies.** Resist the urge to add anything else.

Rationale: FastAPI is the right pick for a webhook receiver — async, fast, trivial JSON handling. `rich` gives us color-coded, well-formatted terminal output for free. The whole thing should be ~150 lines.

---

## Functional requirements

### 1. Configuration

- Load the Memberful webhook signing secret from a `.env` file at the project root, key name `MEMBERFUL_WEBHOOK_SECRET`.
- Provide a `.env.example` file checked into the repo.
- Server port defaults to `8000` but can be overridden by `PORT` env var.
- Log file path defaults to `./events.jsonl` but can be overridden by `LOG_FILE` env var.

### 2. The endpoint

- `POST /webhook` — the receiver. Accepts any JSON payload.
- `GET /health` — returns `{"status": "ok"}`. Useful for sanity-checking via curl after starting the server.

### 3. Signature verification

Memberful signs webhooks as follows (verified against Memberful docs):

- Algorithm: **HMAC-SHA256**, computed over the **raw request body bytes**.
- Key: the signing secret (string) shown in the Memberful dashboard after creating the webhook endpoint.
- Encoding: hex digest, lowercase.
- Header: `X-Memberful-Webhook-Signature`

Implementation rules:

- Compute the expected signature over the **raw bytes** of the request body, not the parsed JSON. (FastAPI: use `await request.body()` before parsing.)
- Compare with `hmac.compare_digest()` to avoid timing attacks. Never use `==`.
- If the header is missing → return `401` with `{"error": "missing signature header"}`.
- If the signature does not match → return `401` with `{"error": "invalid signature"}`. **Still log the attempt to stderr** (timestamp, source IP, header value) so the user can see suspicious activity during the demo.
- If verification passes → continue to logging and pretty-print, then return `200` with `{"status": "ok"}`.

A webhook receiver MUST respond within 15 seconds or Memberful will retry. Do not do any blocking work — log to disk and stdout, return 200, done.

### 4. Pretty-print to terminal

When a verified event arrives, print the following block using `rich`:

```
─────────────────────────────────────────────────────
  📨 subscription.created                  14:23:07
─────────────────────────────────────────────────────
  Member:        John Doe <john.doe@example.com>
  Member ID:     12345
  Plan:          Sample plan ($10.00/month)
  Subscription:  #98765 — active, autorenew: true
  Created:       2025-09-15T22:07:48Z

  [dim]Full payload logged to events.jsonl[/dim]
─────────────────────────────────────────────────────
```

Rules:

- The header line includes the event name (from the `event` field in the payload) and a local-time timestamp.
- Color-code the event name by family:
  - `member_*` → **cyan**
  - `subscription.*` → **green** (created/renewed/activated) or **yellow** (updated) or **red** (deactivated/deleted)
  - `order.*` → **magenta** (purchased) or **red** (refunded/suspended)
  - `download.*` and `plan.*` → **blue**
  - Anything unrecognized → **white**, with a `[?]` prefix so unknown events are obvious.
- For the body, extract and display the most useful 3–6 fields based on event type. A small dispatcher dict mapping event name → formatter function is fine. For unknown events, just dump the top-level keys with `rich.pretty.pprint`.
- Always include "Full payload logged to {LOG_FILE}" as a dim footer hint.

### 5. Structured log file

For every verified event, append one line to `events.jsonl` in this shape:

```json
{"received_at": "2026-04-19T14:23:07.412Z", "event": "subscription.created", "signature_valid": true, "payload": { ...full original payload... }}
```

- One JSON object per line (JSONL format), UTF-8.
- `received_at` is ISO 8601 UTC with millisecond precision.
- Append-only. Never rewrite or truncate.
- If the log file doesn't exist, create it. If the directory doesn't exist, create it.

Failed signatures are also logged to a sibling file `events.invalid.jsonl` with `{"received_at": ..., "reason": "invalid signature", "headers": {...}}` (no payload, since we can't trust it).

### 6. Startup banner

When the server starts, print a banner to stdout:

```
╭───────────────────────────────────────────────────╮
│  Memberful Webhook Inspector                      │
│  Listening on http://localhost:8000/webhook       │
│  Logging to ./events.jsonl                        │
│  Signing secret: ********...4f2a (loaded)         │
╰───────────────────────────────────────────────────╯

Tip: expose this endpoint with `ngrok http 8000`, then paste
the public URL into Memberful → Settings → Webhooks.

Waiting for events…
```

If `MEMBERFUL_WEBHOOK_SECRET` is not set, exit with a clear error message pointing to `.env.example`.

---

## Project structure

```
memberful-webhook-inspector/
├── README.md
├── .env.example
├── .gitignore                  # excludes .env, events.jsonl, events.invalid.jsonl, __pycache__/
├── requirements.txt
├── inspector/
│   ├── __init__.py
│   ├── app.py                  # FastAPI app + endpoints
│   ├── verify.py               # signature verification
│   ├── formatters.py           # event → pretty-print dispatchers
│   └── logger.py               # JSONL append logic
└── tests/
    ├── __init__.py
    └── test_verify.py          # signature verification round-trip + tampered-body rejection
```

Keep it that small. Do not add a `cli.py`, `config.py`, `models.py`, etc. unless they earn their place.

---

## Tests

Required tests in `tests/test_verify.py`:

1. **Valid signature passes.** Compute a known HMAC over a known body with a known secret; assert `verify_signature(body, sig, secret)` returns `True`.
2. **Tampered body fails.** Compute the signature over body A, then call verify with body B and the signature for A. Must return `False`.
3. **Tampered signature fails.** Flip a single character in the signature. Must return `False`.
4. **Wrong secret fails.** Verify with a different secret. Must return `False`.
5. **Empty signature fails.** Pass an empty string as the signature. Must return `False`.

Use `pytest`. No fixtures needed; these are one-liners.

End-to-end testing is manual (use `curl` or the Memberful dashboard's "Send test webhook" button, documented in the README).

---

## README requirements

The README is part of the deliverable. It must include, in this order:

1. **One-sentence description** + a small "What it looks like" terminal screenshot or copy-pasted output block.
2. **Why I built this** — 2–3 sentences. Frame it honestly: built during a Memberful product trial to make it easier to understand what events fire when. Mention that it surfaced [some specific small insight you noticed] — author will fill this in after running it.
3. **Quickstart** — exact commands to clone, install, configure, run, and expose via ngrok. Should be copy-pasteable and work first time.
4. **Verifying it works** — a "Send test webhook" walkthrough using either Memberful's built-in test button or a sample `curl` command.
5. **What gets logged** — show one example pretty-print block and one example JSONL line.
6. **Security notes** — explicitly call out that this is a local dev tool, not production-grade. Note the HMAC verification, the constant-time comparison, and the rejection of unsigned requests.
7. **Future work** — a short list. Sample ideas: SQLite storage, web dashboard, Slack/Discord forwarding, replay tool, Docker image. Mark these as "out of scope for v1."
8. **License** — MIT.

Tone: matter-of-fact, technical, no emoji-spam. One emoji in the opening title line is fine. Write like a senior engineer who built a useful thing.

---

## Acceptance criteria

The project is done when:

- [ ] `pip install -r requirements.txt && python -m inspector.app` starts the server cleanly.
- [ ] A `curl` POST with a valid signature is accepted, pretty-printed, and logged to `events.jsonl`.
- [ ] A `curl` POST with no signature returns 401 and is logged to `events.invalid.jsonl`.
- [ ] A `curl` POST with a wrong signature returns 401 and is logged to `events.invalid.jsonl`.
- [ ] `pytest` passes all five signature tests.
- [ ] README is complete, with a working quickstart and a sample output block.
- [ ] `.env` is in `.gitignore`. `.env.example` is checked in.
- [ ] Total LOC (excluding tests and README) is under 250 lines. If you're over, you're over-engineering.

---

## Out of scope (do not build)

- Persistence beyond JSONL.
- A web UI.
- Forwarding to Slack/Discord/email.
- A configuration file beyond `.env`.
- Multi-tenant / multi-account support.
- Authentication for the inspector itself.
- A package-and-publish step (no PyPI, no Homebrew).

If the agent is tempted to build any of these, stop and add them to "Future work" in the README instead.
