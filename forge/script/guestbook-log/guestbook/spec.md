# Section Zero

- **Document Title:** ST33V Guestbook v1 — Implementation Specification for Codex
- **Document Type:** Build Specification
- **Project:** st33v.com guestbook / page-aware comment system
- **Status:** Draft for implementation
- **Date:** 2026-03-24
- **Author:** ChatGPT
- **Primary Environment:** Arch Linux development host (`cr4y`) and Linux VPS running `nginx`
- **Site Context:** `st33v.com` is a statically generated music site deployed by `rsync`; pages already include a shared SSI footer
- **Implementation Bias:** Language-agnostic, but solutions using **POSIX shell / bash**, **Python**, and **SQLite** are preferred
- **Out of Scope for v1:** AI moderation, accounts, logins, CAPTCHA, social auth, threaded replies, edit/delete by users, notifications, moderation dashboard beyond simple admin utilities
- **Core Principle:** Keep friction low for good-faith participants while still applying strong first-line filtering and abuse resistance from day one

## TL;DR

Build a lightweight, page-aware guestbook/comment system for `st33v.com` that can be reached from the existing SSI footer on every page. A visitor should be able to submit:

1. a display name,
2. a comment in Markdown,
3. with the page context auto-captured,
4. while the system stores useful metadata automatically,
5. and applies robust v1 filtering and moderation safeguards without requiring login or CAPTCHA.

The site itself remains static. The guestbook subsystem may be a small dynamic service or CGI-style endpoint running alongside `nginx`, with comments stored in SQLite. Footer controls should allow a visitor to open the guestbook form and see whether the current page has comments. The system must reject HTML, permit a conservative Markdown subset, rate-limit abuse, use anti-spam techniques such as honeypots, and store moderation-relevant metadata such as IP, user agent, referrer, page path, timestamps, and filtering results.

Codex must produce:

- the implementation,
- a `README.md`,
- a deployment script,
- configuration examples,
- and sensible admin utilities for inspection and moderation.

---

# 1. Purpose

## 1.1 Objective

Implement a **low-friction guestbook / comment layer** for `st33v.com` that feels reminiscent of an old web guestbook, but is modern enough to survive exposure to the public internet.

## 1.2 User Experience Goal

A visitor browsing any song, album, or site page should be able to scroll to the footer and:

1. see a guestbook/comment control,
2. optionally see basic page stats or comment indicators,
3. open a form,
4. submit a comment without creating an account,
5. have the system automatically associate that comment with the page they were on.

## 1.3 Philosophy

This is not intended to be a high-friction identity system. It is intended to invite **good-faith participation** with minimal ceremony. Defensive measures must exist, but they should be mostly invisible to honest participants.

---

# 2. High-Level Requirements

## 2.1 Functional Requirements

The system must:

1. expose guestbook/comment controls from the existing SSI footer on all pages;
2. allow submission of a display name and comment text;
3. automatically capture the current page URL/path;
4. support Markdown input, but **not raw HTML**;
5. store comments in SQLite;
6. collect useful metadata for moderation and diagnostics;
7. apply filtering and anti-abuse measures from day one;
8. allow comments to be retrieved and displayed for a specific page;
9. optionally allow a global guestbook view spanning all pages;
10. provide simple admin tools for review and moderation;
11. be deployable on the existing VPS with minimal moving parts.

## 2.2 Non-Functional Requirements

The system should be:

- simple to operate;
- easy to back up;
- easy to inspect with shell tools;
- resilient against obvious spam and script abuse;
- compatible with a mostly static site model;
- modest in resource use;
- understandable without a large framework.

## 2.3 Preferred Implementation Style

The implementation should lean toward:

- small, inspectable components;
- shell scripts for deployment and maintenance tasks;
- Python for request handling, sanitization, Markdown rendering, and moderation logic;
- SQLite for persistent storage;
- `nginx` as reverse proxy and static file server.

Large frameworks are not prohibited, but they are not preferred. A small Python app, CGI-like handler, FastCGI service, or similarly lightweight architecture is preferred over a heavyweight application stack.

---

# 3. Conceptual Model

## 3.1 Two Modes

The system should support two conceptual modes:

### 3.1.1 Page-Scoped Comments
Comments attached to a specific page, such as:

- a song page,
- an album page,
- an about page,
- or any other content page.

### 3.1.2 Global Guestbook
A site-wide guestbook stream showing all approved comments across the site.

This may be implemented from the same underlying data model by treating page association as first-class and adding aggregate views.

## 3.2 Footer as Universal Entry Point

Because every page already includes the SSI footer, the footer should become the universal control plane for the guestbook system. It may contain:

- a “Leave a comment” control,
- a “View comments” control,
- a compact comment count,
- optional lightweight stats later.

The footer may be visually expanded and redesigned as needed.

---

# 4. Architecture

## 4.1 Overall Shape

The recommended architecture is:

1. **Static site content** served by `nginx`
2. **SSI footer** included across pages
3. **Guestbook backend endpoint** for submit/retrieve/admin actions
4. **SQLite database** for storage
5. **Admin utilities** as CLI scripts
6. **Deployment script** to install/update the guestbook subsystem

## 4.2 Suggested Deployment Topology

A suitable topology is:

- static pages remain under existing document roots;
- guestbook backend runs as a local service bound to `127.0.0.1:<port>` or via Unix socket;
- `nginx` proxies `/guestbook/...` routes to that backend;
- SQLite DB and writable runtime state live outside the static web tree, e.g. under `/var/lib/st33v-guestbook/`;
- logs live under `/var/log/st33v-guestbook/` or integrate with `journalctl`.

## 4.3 Avoided Architecture

Avoid:

- requiring a full CMS,
- requiring a Node-based app unless clearly justified,
- embedding writable data inside the static site deploy tree,
- storing comments as ad hoc flat files unless there is a strong reason.

SQLite is the preferred persistence layer.

---

# 5. Deliverables Required from Codex

Codex must produce, at minimum:

## 5.1 Required Files

1. `README.md`
2. deployment script, e.g. `deploy.sh`
3. application source code
4. SQLite schema creation or migration script(s)
5. example `nginx` configuration snippet(s)
6. example systemd unit(s), if a persistent service is used
7. admin utility scripts
8. default configuration file or `.env.example`-style equivalent
9. sample SSI footer integration snippet or instructions
10. sample moderation / guideline text for display in UI

## 5.2 README Content Requirements

`README.md` must include:

1. project overview,
2. architecture summary,
3. dependencies,
4. installation instructions,
5. configuration variables,
6. deployment instructions,
7. database location and backup guidance,
8. moderation workflow,
9. admin commands,
10. troubleshooting notes,
11. upgrade/update procedure,
12. rollback notes if practical.

## 5.3 Deployment Script Requirements

The deployment script must:

1. be idempotent or as close as practical;
2. support installation on the VPS;
3. create needed directories with correct permissions;
4. install or verify systemd service files if used;
5. initialize the database if absent;
6. install/update code;
7. install/update configuration templates;
8. reload/restart the service safely;
9. validate `nginx` config if it modifies or depends on it;
10. print clear status output.

The exact particulars may be finalized during implementation, but the script must exist from the outset.

---

# 6. Data Model

## 6.1 Core Table: Entries

A core `entries` table should include fields roughly equivalent to the following:

- `id` — integer primary key
- `created_utc` — ISO 8601 or epoch timestamp
- `updated_utc` — nullable
- `status` — enum-like text field (`pending`, `approved`, `rejected`, `spam`, `hidden`)
- `display_name` — user-provided name
- `comment_raw` — original submitted Markdown/plaintext
- `comment_rendered` — sanitized rendered HTML or cached rendered output
- `page_url` — canonical URL if available
- `page_path` — normalized path component
- `page_title` — optional, if captured client-side or inferred
- `referrer` — HTTP referrer if present
- `ip_address` — remote IP, ideally normalized
- `ip_hash` — optional privacy-preserving hash for grouped analysis
- `user_agent` — raw UA
- `accept_language` — optional
- `submission_token` — optional idempotency token if used
- `honeypot_value` — hidden-field capture for diagnostics
- `filter_score` — numeric or text summary
- `filter_flags` — serialized JSON/text of triggered filters
- `source_kind` — e.g. `web_form`
- `notes_internal` — admin notes
- `is_deleted` — soft delete marker if desired

## 6.2 Optional Table: Page Stats

A `page_stats` table may track aggregate counts for display efficiency:

- `page_path`
- `comment_count_approved`
- `comment_count_pending`
- `last_comment_utc`

This is optional; counts can also be derived dynamically.

## 6.3 Optional Table: Moderation Events

A `moderation_events` table may track admin actions:

- `id`
- `entry_id`
- `event_utc`
- `action`
- `actor`
- `notes`

Useful, but not strictly required for v1.

## 6.4 Optional Table: Rate Limits / Abuse Signals

A small table for rate limiting or event history may be used, for example:

- `id`
- `event_utc`
- `ip_address`
- `page_path`
- `action`
- `result`

This can also be derived from logs instead.

---

# 7. Submission Flow

## 7.1 Form Fields Visible to User

Visible fields should be minimal:

1. **Name**
2. **Comment**

Optional visible field:

3. a consent/acknowledgment checkbox for the site’s good-faith expectations

This checkbox should be used only if it improves clarity without becoming annoying.

## 7.2 Fields Captured Automatically

The system should automatically capture as much of the following as practical:

- current page URL/path
- referrer
- IP address
- user agent
- timestamp
- accept-language
- request headers useful for diagnostics
- whether filters triggered
- whether submission was approved, held, or rejected

## 7.3 Hidden Fields

The form should include at least one hidden honeypot field. It may also include:

- a page path hidden field
- a timestamp issued at form render time
- a lightweight anti-replay token if desired

These should be server-validated, not trusted blindly.

## 7.4 Submission Outcome

On submit, the system should return one of the following outcomes:

1. **accepted and visible**
2. **accepted pending review**
3. **rejected with generic message**
4. **rate-limited / temporarily blocked**

User-facing messages should be polite and non-revealing.

---

# 8. Filtering, Moderation, and Abuse Prevention

## 8.1 This Is Mandatory for v1

Filtering and moderation protections are not optional. The form must not be exposed publicly without them.

## 8.2 Filtering Layers

The system should use a layered approach.

### 8.2.1 Input Validation

Reject or constrain:

- empty names,
- empty comments,
- overlong names,
- overlong comments,
- malformed requests,
- invalid encodings,
- unexpected content types.

### 8.2.2 HTML Rejection

Raw HTML must not be accepted as displayable content.

Either:

1. reject comments containing HTML outright, or
2. strip/escape all HTML before processing Markdown.

The safer default is to treat submitted text as plain text / Markdown source and render from a trusted renderer with HTML disabled.

### 8.2.3 Markdown Policy

Allow a conservative Markdown subset such as:

- paragraphs
- line breaks
- emphasis
- strong
- links
- unordered lists
- ordered lists
- blockquotes
- code spans

Potentially disallow for v1 unless safe rendering is trivial:

- images
- raw HTML blocks
- tables
- embedded content

Links should be sanitized. Dangerous URI schemes such as `javascript:` must be rejected.

### 8.2.4 Honeypot

Add at least one hidden field that normal users will not fill in. If filled, flag as spam or reject.

### 8.2.5 Rate Limiting

Implement rate limiting by IP and/or hashed IP. Suggested minimum controls:

- max submissions per IP per hour
- max submissions per IP per day
- cooldown between submissions
- optional per-page limits

Use conservative defaults configurable via config file.

### 8.2.6 Keyword and Phrase Filters

Support configurable blocklists / heuristics for:

- common spam phrases,
- scam terms,
- abusive profanity categories if desired,
- suspicious link-heavy content,
- repeated gibberish or machine-like spam.

This should be implemented in a configurable way, ideally via text or YAML/JSON rule files.

### 8.2.7 URL Heuristics

Flag content that includes:

- too many URLs,
- shortened URLs,
- suspicious TLD clusters,
- repeated domain spam.

### 8.2.8 Structural Heuristics

Flag submissions with patterns such as:

- repeated identical characters,
- excessive uppercase,
- excessive emoji or punctuation,
- nonsense repeated tokens,
- form fields filled too quickly if timing checks are used.

### 8.2.9 Profanity / Slur Filtering

Implement a configurable profanity/slur filter with the following principles:

- configurable severity levels;
- support for flagging rather than always hard-rejecting;
- maintainability via local wordlists;
- false positives should be manageable.

Codex may use an existing open-source library if lightweight and appropriate, but the system should not depend exclusively on third-party hosted APIs.

### 8.2.10 Approval Strategy

Recommended v1 strategy:

- obviously clean submissions: auto-approve
- suspicious but not extreme: mark `pending`
- obvious spam/abuse: mark `spam` or reject

This gives some tolerance while preserving site quality.

## 8.3 Third-Party Dependency Policy

Prefer local/self-hosted filtering logic for v1.

Third-party services such as Akismet-like services may be made optional, but must not be a hard dependency unless clearly justified. The project should remain operable without external paid APIs.

## 8.4 Bot Philosophy

The system should not assume “bot = bad.” It should assume “bad behavior = bad.” Well-behaved automated participants should be tolerated if their behavior remains within the good-faith boundaries and rate limits.

## 8.5 Good-Faith Statement

The UI should include or link to a short statement of expectations. Do not label it “Code of Conduct.” Use language such as:

- “Good-Faith Participation”
- “Notes for Visitors”
- “House Style”
- “How to Sign the Book”

This text should set tone without bureaucratic heaviness.

---

# 9. Rendering and Display

## 9.1 Display Contexts

Support at least:

1. page-specific comment list,
2. optional global guestbook page.

## 9.2 Approved Content Only

Public display should show only approved comments unless an explicit admin/debug mode is used.

## 9.3 Rendering Rules

Rendered output must:

- escape unsafe content,
- disable raw HTML,
- sanitize links,
- present timestamps clearly,
- show display name,
- show page association where relevant.

## 9.4 Ordering

Default ordering should be newest first, unless old-school guestbook chronology is preferred. Make ordering configurable.

## 9.5 Empty States

Provide decent empty-state messaging such as:

- “No comments yet.”
- “Be the first to sign the book for this page.”

---

# 10. SSI Footer Integration

## 10.1 Footer Role

The SSI footer is the common insertion point and may be expanded substantially.

## 10.2 Footer Requirements

The footer should be able to show some or all of:

- “Leave a comment”
- “View comments”
- comment count for the current page
- optional global guestbook link
- optional note pointing to the good-faith statement

## 10.3 Page Context Propagation

The footer integration must reliably provide the current page context to the guestbook form. Possible methods include:

- server-side embedding of path metadata,
- client-side extraction from `window.location`,
- hidden form fields populated via JS.

The backend must still validate and normalize page association server-side.

## 10.4 Progressive Enhancement

A JavaScript-enhanced UI is acceptable, but the basic interaction should remain reasonably functional without elaborate client-side frameworks.

---

# 11. API / Endpoint Design

## 11.1 Suggested Routes

Codex may adjust these, but a structure like the following is suitable:

- `GET /guestbook/form` — returns form HTML fragment or page
- `POST /guestbook/submit` — submit comment
- `GET /guestbook/page?path=...` — fetch comments for a page
- `GET /guestbook/all` — global guestbook view
- `GET /guestbook/guidelines` — good-faith statement

Admin endpoints may be omitted from public HTTP and implemented as CLI utilities instead, which is preferred for v1.

## 11.2 Response Formats

Support simple HTML output first. JSON endpoints are optional but useful for footer widgets or future extensions.

## 11.3 Security Posture

Do not expose rich admin APIs publicly in v1 unless properly protected.

---

# 12. Admin and Maintenance Tools

## 12.1 CLI Utilities

Provide shell-friendly admin tools for:

- listing pending comments,
- approving a comment,
- marking spam,
- hiding/rejecting a comment,
- dumping counts,
- searching entries,
- exporting DB rows,
- vacuuming or maintaining the SQLite DB if needed.

These may be shell scripts calling Python utilities or a single Python admin CLI.

## 12.2 Example Admin Commands

The exact interface is up to Codex, but examples might include:

- `guestbook-admin list-pending`
- `guestbook-admin approve <id>`
- `guestbook-admin spam <id>`
- `guestbook-admin stats`
- `guestbook-admin export --format csv`

## 12.3 Logging

Application events should be loggable via:

- `journalctl` for systemd-managed service,
- or a dedicated log file.

At minimum, log:

- submission attempts,
- filter outcomes,
- rejections,
- rate-limit events,
- admin actions.

---

# 13. Database and File Locations

## 13.1 Preferred Paths

Suggested path layout:

- code: `/opt/st33v-guestbook/` or similar
- runtime data: `/var/lib/st33v-guestbook/`
- logs: `/var/log/st33v-guestbook/`
- config: `/etc/st33v-guestbook/`
- systemd units: standard systemd locations
- `nginx` snippets: existing site config layout

Codex may adapt this to local conventions but should keep writable state outside the static deploy tree.

## 13.2 Backups

README must document how to back up:

- SQLite DB file,
- config file(s),
- custom wordlists / moderation rules.

Because SQLite is central, backup instructions must be explicit and sane.

---

# 14. Nginx Integration

## 14.1 Reverse Proxy

The preferred pattern is `nginx` reverse proxying a local backend or Unix socket.

## 14.2 Static Site Separation

Do not contaminate the static site tree with writable backend state.

## 14.3 Config Snippet

Codex must provide an `nginx` snippet or full example showing:

- route mapping for guestbook endpoints,
- any headers required for correct client IP / referrer handling,
- safe defaults,
- reload instructions.

## 14.4 Existing SSI

The existing SSI setup must remain compatible. Codex should specify exactly how to add guestbook controls into the current footer include.

---

# 15. Service Management

## 15.1 Systemd

If the backend is a long-running service, provide a systemd unit. This is preferred.

## 15.2 Systemd Requirements

The unit should:

- run as a dedicated user if appropriate,
- set working directory,
- point to config cleanly,
- restart on failure,
- log clearly.

## 15.3 One-Shot / CGI Alternative

If Codex chooses a CGI/FastCGI model instead, justify it in the README and still provide deployability and maintainability comparable to a small service.

---

# 16. Configuration

## 16.1 Config File

Use a simple configuration mechanism, such as:

- `.env`,
- INI,
- TOML,
- YAML,
- or a Python config file.

Keep it simple.

## 16.2 Configurable Values

At minimum, make these configurable:

- DB path
- bind address / socket path
- moderation mode
- max name length
- max comment length
- rate-limit thresholds
- allowed Markdown features
- wordlist file paths
- logging mode / level
- whether suspicious entries auto-pend or auto-reject

---

# 17. Validation Rules

## 17.1 Name Field

Recommended defaults:

- required
- trim whitespace
- minimum 1 non-space character
- maximum e.g. 80 characters
- reject obviously machine-garbled or control characters

## 17.2 Comment Field

Recommended defaults:

- required
- trim outer whitespace
- minimum sensible length, perhaps 2 or 3 characters
- maximum e.g. 2000–5000 characters, configurable
- reject invalid UTF-8 or binary-like junk
- render Markdown with safe sanitization

## 17.3 Page Path

Normalize to a canonical path format where possible. Prevent arbitrary injection of foreign URLs.

---

# 18. Privacy and Data Handling

## 18.1 Internal Metadata Storage

The system should store moderation-relevant metadata such as IP and user agent, but public display should not expose these.

## 18.2 Public Disclosure

Do not publicly display:

- IP address,
- user agent,
- referrer,
- internal filter scores.

## 18.3 Retention

README should mention a retention policy or at least where such a policy can be configured later.

## 18.4 Hashing

Consider storing both raw IP and hashed IP, or only hashed IP if operationally sufficient. Codex may recommend the best compromise, but the implementation should keep moderation workable.

---

# 19. Suggested Moderation Defaults

## 19.1 Default Outcome Matrix

Suggested behavior:

- **clean text, no suspicious markers:** approve
- **contains mild flagged terms or unusual structure:** pending
- **honeypot hit, extreme link spam, or obvious scam:** reject or spam
- **rate-limit exceeded:** temporarily reject

## 19.2 Admin Review

Pending items should be easy to review from CLI.

## 19.3 Soft Delete

Prefer soft hide/status changes over destructive deletion in routine workflows.

---

# 20. UI Notes

## 20.1 Tone

The UI should feel welcoming, a little old-web in spirit, but not kitsch unless Codex finds a tasteful expression of that.

## 20.2 Footer Control Language

Possible labels:

- “Sign the guestbook”
- “Leave a note”
- “Comments”
- “View the book”

Codex may choose the wording, but it should be simple.

## 20.3 Good-Faith Text

Codex should include a short, non-bureaucratic statement. Example intent:

- be sincere,
- be respectful,
- no spam,
- no scams,
- no hostile abuse,
- links may be filtered,
- comments may be moderated.

---

# 21. Testing Requirements

## 21.1 Minimum Test Coverage

Codex should provide at least lightweight tests or test procedures for:

- valid submission
- empty submission rejection
- HTML stripping/rejection
- Markdown rendering safety
- honeypot detection
- rate limiting
- spam phrase detection
- page association
- admin approval flow

## 21.2 Manual Test Plan

README should include a manual smoke test sequence for the VPS deployment.

---

# 22. Observability and Diagnostics

## 22.1 Logs

Logs should make it easy to answer:

- was a comment submitted?
- why was it rejected or pended?
- what filters triggered?
- is rate limiting working?
- is the DB writable?
- is `nginx` proxying correctly?

## 22.2 Debug Mode

A limited debug mode is acceptable for local testing, but do not enable unsafe verbose leakage in production.

---

# 23. Implementation Preferences for Codex

## 23.1 Language Guidance

The system should be language-agnostic in principle, but the preferred implementation stack is:

- **shell scripts** for deployment and admin glue,
- **Python** for backend logic,
- **SQLite** for storage.

## 23.2 Shell Affinity

Where shell scripts make sense, use them. For example:

- deployment,
- backup,
- DB inspection wrappers,
- service reload helpers,
- export jobs.

## 23.3 Python Responsibilities

Python is a good fit for:

- request handling,
- Markdown rendering,
- sanitization,
- filtering logic,
- admin CLI,
- SQLite interactions.

## 23.4 SQLite Responsibilities

SQLite should handle:

- durable storage,
- indexing,
- filtering state,
- admin lookup queries.

---

# 24. Explicit Non-Goals for v1

Do not spend v1 effort on:

- AI moderation
- user accounts
- OAuth
- social reactions beyond the simplest future-proofing
- complex frontend frameworks
- real-time websockets
- threaded conversation models
- distributed databases
- external SaaS dependence unless optional

The priority is a solid, simple, low-friction, defensible first release.

---

# 25. Acceptance Criteria

The implementation is acceptable when all of the following are true:

## 25.1 Core Behavior

1. a visitor can reach the guestbook from the footer on any page;
2. the current page is automatically associated with the submission;
3. the visitor can submit a name and Markdown comment;
4. HTML is not accepted/rendered unsafely;
5. comments are stored in SQLite;
6. approved comments can be viewed per page.

## 25.2 Moderation and Safety

7. honeypot exists and works;
8. rate limiting exists and works;
9. basic spam/profanity filtering exists and works;
10. suspicious comments can be marked pending;
11. admin can review and approve via CLI.

## 25.3 Operational Deliverables

12. a `README.md` exists and is usable;
13. a deployment script exists and is usable;
14. config examples exist;
15. `nginx` integration instructions exist;
16. service management instructions exist.

## 25.4 Maintainability

17. code layout is understandable;
18. writable data lives outside the static site tree;
19. logs and failure modes are inspectable;
20. the implementation is modest and practical for a single-operator VPS workflow.

---

# 26. Suggested Build Plan for Codex

Codex should proceed in roughly this order:

## 26.1 Phase 1 — Skeleton

1. create project structure
2. define config format
3. define SQLite schema
4. build minimal backend with health check and submit endpoint

## 26.2 Phase 2 — Moderation Basics

5. implement validation
6. implement Markdown-safe rendering
7. implement honeypot
8. implement rate limiting
9. implement blocklist/profanity hooks
10. implement status workflow (`approved` / `pending` / `spam`)

## 26.3 Phase 3 — Display and Integration

11. implement page comment retrieval
12. implement global guestbook view
13. integrate SSI footer controls
14. expose comment count for page if practical

## 26.4 Phase 4 — Ops

15. add admin CLI
16. add logging
17. add deploy script
18. add systemd unit
19. add `nginx` example config
20. write README

---

# 27. Questions Codex May Resolve During Implementation

Codex has discretion to resolve these during the build:

1. whether to use a tiny Python web framework or stdlib HTTP approach;
2. exact Markdown renderer and sanitizer;
3. exact config format;
4. exact file layout;
5. exact admin CLI syntax;
6. exact moderation thresholds;
7. whether page comment count is computed live or cached.

But the implementation must preserve the requirements and philosophy of this spec.

---

# 28. Final Instruction to Codex

Implement a **practical v1 guestbook/comment system** for `st33v.com` that:

- fits a static-site-plus-small-backend architecture,
- uses SQLite,
- prefers shell/Python tooling,
- integrates cleanly with the existing SSI footer,
- captures page context automatically,
- stores useful moderation metadata,
- allows Markdown but not unsafe HTML,
- includes robust first-line filtering and abuse resistance from day one,
- and ships with a real `README.md` and a real deployment script.

Focus on clarity, maintainability, small moving parts, and operational sanity.

---
## Appendix A — Suggested Directory Layout

This is illustrative only.

```text
/opt/st33v-guestbook/
    app/
    bin/
    templates/
    static/
    migrations/
    README.md

/etc/st33v-guestbook/
    config.toml
    blocklist.txt
    profanity.txt

/var/lib/st33v-guestbook/
    guestbook.db

/var/log/st33v-guestbook/
    app.log
```text

## Appendix B — Suggested Public UI Text
B.1 Guestbook Invitation

“Leave a note for this page.”

B.2 Good-Faith Participation Text

“This guestbook is for sincere remarks, responses, and sightings from fellow travellers. Spam, scams, and hostile nonsense are unwelcome. Comments may be filtered or moderated.”

## Appendix C — Suggested Admin Utility Scope
list pending
approve by id
reject by id
mark spam by id
show recent submissions
show per-page counts
export submissions
re-render rendered comment cache if renderer changes
Appendix D — Suggested Metadata to Capture
timestamp
page path
canonical URL if available
referrer
IP
hashed IP
user agent
accept language
filter result
moderation status
honeypot hit
rate-limit hit
