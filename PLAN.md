# MLS Software Internship — 6-Week Plan

**Intern:** James Mitchell
**Supervisor:** Stephen Mitchell, Mitchell Land Surveyors Pty Ltd
**Duration:** 6 weeks, full-time
**Status:** DRAFT — subject to change after discussion with James

---

## Overview

This plan covers six weeks of full-time software development work across multiple projects. The work has two parallel goals that reinforce each other:

1. **Business value** — build tools that save real time in a NSW land surveying practice
2. **Career value** — build a public portfolio of real, working software that makes James attractive to employers in the AEC (architecture, engineering, construction) sector and any company building AI-powered tools

The target audience for employment is **not big tech**. The realistic near-term market is:
- Surveying and engineering firms with software needs
- Spatial data and property technology companies
- Councils and government agencies dealing with land and planning data
- Any business building internal AI tools (relevant right now across all industries)

James finishes his degree at the end of 2026. These 6 weeks should produce a portfolio he can talk about confidently in interviews.

---

## Repositories

| Repo | Language | Purpose | Exists? |
|---|---|---|---|
| `mls-spatial` | Python | NSW spatial search service — the main project | Yes |
| `mls-infotrack` | Python | InfoTrack API wrapper service | Create Week 2 |
| `mls-assistant` | Python + JS | RAG-powered business manual assistant | Upgrade Week 4 |
| `mls-spatial-viewer` | Python + JS | Leaflet web map viewer for spatial search | Create Week 5 |
| AutoCAD add-in | C# | Draws spatial search results in Civil 3D | Create Week 6 |
| `MLSSurveyManager` | C# | Stephen's job management system (existing) | Yes — Week 3 |

All Python repos follow the same pattern: FastAPI service, structured as a package, with a README, tests, Docker, and CI.

---

## Week 1 — mls-spatial: Fix, Test, Harden, Expand

**Project:** `mls-spatial`
**Goal:** Fix all known issues, add engineering hygiene, and implement the first round of new features from the updated SPEC.

### Tasks

**Day 1 — Read everything first**
- Read SPEC.md in full. Understand every section before writing code.                   # DONE
- Read all existing service/ files: models.py, search.py, export.py, server.py, api/    # DONE
- Read the three GitHub issue descriptions                                              # DONE
- Update SPEC.md: correct the "Current position" line, mark Phase 1 complete            # DONE
- Do not write any feature code until this is done                                      # DONE

**Bug fixes (Issues #1, #2, #3)**
- Fix section number in subject_lot label — 4 places (Issue #3)                         # DONE
- Add missing mark fields to export.py GeoJSON output (Issue #2)                        # DONE
- Add `marks_radius_m` parameter to search.py and server.py (Issue #1)                  # DONE

**Code cleanup**
- Delete commented-out dead code in search.py (lines 36-51)                             # DONE
- Fix `spatialsearch.py` — add `if __name__ == "__main__"` guard or delete it           # DONE deleted
- Fix broken test imports in tests/test_survey_marks.py                                 # DONE

**New features**
- `GET /mark/{mark_type}/{mark_number}` endpoint — uses `[MARK_ATTR]` attribute query                   # DONE
- `GET /mark/{mark_type}/{mark_number}/sketch` endpoint — fetches LSP PDF from `[SKETCH]`               # check with surveyor if still doing this (need to find correct API to use)
- Surface level AHD at subject address — add to `Address` model, query `[ELEV]`, include in GeoJSON     # check with surveyor there is grid ahd level for address but not specifically for model address

**Engineering hygiene**
- Rewrite all tests with mocked HTTP using `pytest-httpx` (no live API calls)           # DONE
- Add `Dockerfile` and `docker-compose.yml`                                             # DONE needs testing though 
- Add GitHub Actions workflow — runs pytest on every push                               # not done
- Add SQLite search history (`service/history.py`, `GET /history` endpoint)             # DONE
- Convert NSW API calls to async using `httpx` + `asyncio`                              # not done

### Definition of done
- All 3 GitHub issues closed with a PR each                                             # no pr
- `pytest tests/` passes with no live API calls                                         # DONE
- Green CI badge visible on the GitHub repo                                             # not done
- `docker build` succeeds                                                               # not tested
- `/mark/TS/2761` returns a SurveyMark JSON object                                      # needs to be checked
- `/mark/TS/2761/sketch` returns a PDF                                                  # not done
- Surface level appears in the `search` block of GeoJSON output                         # needs to be checked
- `GET /history` returns the last 20 searches                                           # DONE

### Career skills demonstrated
- Bug triage and issue ownership (closes 3 public GitHub issues)
- Mocked unit testing (interviewers always ask about this)
- Docker and CI/CD (hygiene items visible on the repo)
- Async Python (httpx/asyncio)
- SQLite and basic database design

Note for next week # must review new test cases made for week 1
---                         

## Week 2 — mls-infotrack: New Python Service

**Project:** `mls-infotrack` (new repo)
**Goal:** Build a Python FastAPI service that wraps the InfoTrack API for ordering property title searches and plans.

InfoTrack is the major Australian legal/property services company. Every surveyor, property lawyer, and builder knows InfoTrack. Integrating their API into a job management system directly saves time and removes manual steps.

### Tasks

- Read and understand the InfoTrack API documentation thoroughly before writing code
- Set up new repo with the same structure as mls-spatial (FastAPI, service/ package, tests, Docker, CI)
- Build an API client (`service/api/infotrack.py`) — authentication, error handling, rate limits
- Identify and document what can be ordered: title searches, current title details, plan copies, dealings
- Build endpoints:
  - `GET /title?lot={lot}&plan={plan}` — fetch current title details
  - `POST /order/title` — place a title search order
  - `POST /order/plan` — order a plan copy
  - `GET /order/{order_id}` — check order status
- Write mocked tests for all endpoints
- Document findings: what the API returns, what fields are available, what costs what

### Definition of done
- New public repo `mls-infotrack` with README, tests, Docker, CI badge
- Can order a title search via the API and retrieve the result programmatically
- Mocked tests pass in CI
- README clearly explains what the service does and why it exists

### Career skills demonstrated
- Commercial REST API integration with authentication
- Service design (new repo, clean architecture)
- Research and documentation (reading API docs, writing findings)

---

## Week 3 — InfoTrack into MLSSurveyManager

**Project:** `MLSSurveyManager` (C# ASP.NET Core Razor Pages)
**Goal:** Wire the InfoTrack service into the existing job management system so a title search can be ordered directly from a Job or Proposal page.

This week involves C# development on a production application. Stephen will provide guidance on the ASP.NET/Razor Pages patterns and the existing codebase.

### Tasks

- Read the existing MLSSurveyManager codebase — understand the Job, Proposal, and CT (Certificate of Title) models
- Add a "Order Title Search" button/card to the Job Edit page
- `Pages/Api/InfoTrackSearch.cshtml.cs` — new API page that calls the `mls-infotrack` service
- On successful order: populate CT fields on the job record automatically
- Handle errors gracefully — InfoTrack unavailable, address not found, order failed
- Test end-to-end: from the Job page, order a real title search, see result appear in the CT record

### Definition of done
- From a Job Edit page, click "Order Title" and have the CT details populate automatically
- Errors shown clearly to the user without crashing
- Works end-to-end against the live InfoTrack API

### Career skills demonstrated
- C# and ASP.NET Core (adds a second language to the portfolio)
- Cross-language system integration (Python service called from C# app)
- Working on an existing production codebase (not just greenfield)

---

## Week 4 — mls-assistant: RAG-Powered Business Assistant

**Project:** `mls-assistant` (upgrade existing HTML prototype to Python + RAG)
**Goal:** Transform the existing single-file HTML chat app into a proper FastAPI backend with Retrieval Augmented Generation (RAG) so the business manual can be indexed and searched rather than pasted wholesale into every prompt.

RAG (Retrieval Augmented Generation) is currently the most in-demand AI engineering skill in the industry. Every company building internal AI tools is building RAG systems. This project makes James directly hireable for that work.

### What RAG means in practice
Instead of sending the entire business manual with every message (expensive, limited), you:
1. Split the manual into chunks (one paragraph or procedure per chunk)
2. Convert each chunk to a vector (embedding) that represents its meaning
3. When a question arrives, find the 3-5 most relevant chunks
4. Include only those chunks in the Claude prompt

The result: cheaper, faster, and more accurate answers.

### Tasks

- Study the existing `mls-assistant.html` thoroughly — understand every function before rewriting
- Fix the existing bug: `init()` references `rulebook-input` but the element is `rulebook-textarea`
- Set up new repo structure: FastAPI backend + frontend/ HTML
- Build the RAG pipeline (`service/rag.py`):
  - Document chunking (split by section/paragraph)
  - Embedding using `sentence-transformers` (runs locally, no API key)
  - Vector storage using `chromadb` (lightweight local vector database)
  - Retrieval: embed incoming question, find top-4 matching chunks
- Build API endpoints:
  - `POST /chat` — accepts question + conversation history, returns streamed response
  - `POST /knowledge/upload` — upload a .txt or .md document, chunk and index it
  - `GET /knowledge` — list indexed documents
- Add streaming (Server-Sent Events) — response appears word by word like ChatGPT
- Update the HTML frontend to talk to the local backend instead of calling Anthropic directly
- Write a clear README with a diagram explaining how RAG works

### Definition of done
- Upload Stephen's business manual via the web UI
- Ask "how do I file a title search invoice?" — assistant retrieves the right section and answers correctly
- Streaming works — response appears progressively
- README explains RAG clearly enough for a non-technical reader
- Repo is public and presentable

### Career skills demonstrated
- RAG architecture (the #1 AI skill employers hire for right now)
- Vector embeddings and similarity search
- Streaming API responses (Server-Sent Events)
- The Anthropic SDK / Claude API
- Making a real AI tool that solves a real problem

---

## Week 5 — mls-spatial-viewer: Web Map + New Search Modes

**Project:** `mls-spatial-viewer` (new repo) + additions to `mls-spatial`
**Goal:** Build a Leaflet.js web map that calls the `/search` endpoint and displays results interactively. Also add folio search and polygon search to `mls-spatial`. Generate a PDF search report. Deploy the viewer live.

The web viewer is the most demo-able item in the portfolio. It is accessible to anyone via a URL — no AutoCAD, no Python, no setup required. This is what you show at an interview or to a prospective employer.

### Tasks

**mls-spatial additions**
- Folio search: `GET /search?folio=102/DP574558` — see SPEC for implementation details
- Polygon search: accept GeoJSON polygon geometry — lots bounded by polygon, marks by centroid + radius
- PDF report (`service/report.py`): A4 report with CRE map, lot table, mark table with bearing/distance, plan list

**mls-spatial-viewer (new repo)**
- Simple Python FastAPI app that serves a single HTML page
- Leaflet.js map centred on NSW
- Search form: address input, radius sliders (lots and marks separately), folio input option
- Draw polygon/polyline mode using `leaflet-draw` plugin
- On search: call local mls-spatial `/search`, render:
  - Lots as coloured polygons (blue = compiled, red shaded by age = surveyed)
  - Subject lot with marker
  - Survey marks as point symbols with popups showing class, AHD height, coordinates, CSF
- "Download PDF report" button calls `/full-search` and opens the PDF
- Deploy to Render or Railway free tier so it is publicly accessible

### Definition of done
- Visit the live URL, type an address, see lots and marks on a map
- Mark popup shows: type, number, GDA class, AHD height, easting/northing, CSF
- Folio search works from the form
- Polygon drawn on map returns lots within the polygon
- PDF report downloads with lot table, mark table, and CRE map image
- `mls-spatial-viewer` is a public repo with a README linking to the live demo

### Career skills demonstrated
- Geospatial web development (Leaflet.js, GeoJSON)
- Frontend JavaScript (not a toy project — a real interactive application)
- Cloud deployment (free tier, but demonstrates the skill)
- PDF generation (reportlab)
- New public repo with a live demo URL

---

## Week 6 — AutoCAD Spatial Add-in

**Project:** Standalone C# AutoCAD/Civil 3D add-in
**Goal:** Build a Civil 3D add-in that calls the `mls-spatial` `/search` endpoint and draws all lots and survey marks directly in AutoCAD. Pair-program with Stephen who will guide the AutoCAD API parts.

This completes the original Phase 2 vision from the SPEC. It is the most impressive demo for surveying and engineering firms — type an address in AutoCAD and watch the cadastral search draw itself.

### Tasks (pair with Stephen)

- Set up a new standalone Visual Studio project referencing AutoCAD and Civil 3D assemblies
- A simple AutoCAD command: `MLSSEARCH`
- Command prompts for address, lot radius, mark radius
- Calls `GET /health` first — shows error if service not running
- Calls `GET /search` with the provided parameters
- Parses GeoJSON FeatureCollection response:
  - Lots: draw closed polylines on a dedicated layer, colour by `is_surveyed` and `registration_date`
  - Subject lot: add a marker block at centroid
  - Survey marks: insert a block/point, add attribute text (mark number, GDA class, AHD height)
- Zoom to extents of drawn features
- Basic error handling: address not found, service unavailable

### Definition of done
- From a blank Civil 3D drawing, run `MLSSEARCH`, type an address — lots and marks are drawn
- Lots coloured correctly (blue compiled, red-shaded surveyed by age)
- Survey marks labelled with number and class
- Works on a real NSW address against the live local service

### Career skills demonstrated
- C# and .NET (second language, production context)
- AutoCAD/Civil 3D .NET API (rare skill, very valuable in AEC)
- Cross-language integration (C# consuming a Python API)
- Completing the full-stack vision of a real project

---

## Portfolio Summary at Week 6

| Repo | What it shows |
|---|---|
| `mls-spatial` | Python, FastAPI, async, GeoJSON, government API integration, Docker, CI, testing, SQLite |
| `mls-infotrack` | Commercial API integration, service design, documentation |
| `mls-assistant` | RAG, vector embeddings, streaming, Claude API, real AI engineering |
| `mls-spatial-viewer` | Geospatial frontend, Leaflet.js, live deployed demo |
| AutoCAD add-in | C#, AutoCAD .NET, Civil 3D, cross-language integration |

All work has been deployed or used in a real NSW land surveying practice. This is production experience, not toy projects.

---

## Career Framing

Each project should be framed in its README as a general-purpose engineering solution, not just internal tooling:

- `mls-spatial` — "A Python FastAPI service that integrates NSW government spatial APIs to return cadastral search results as GeoJSON. Used in production at a land surveying firm."
- `mls-infotrack` — "A Python microservice wrapping a commercial property data API with authenticated ordering. Deployable pattern for any property, legal, or conveyancing firm."
- `mls-assistant` — "A RAG-based knowledge assistant that indexes internal documentation and answers staff questions using retrieved context. Generalisable to any organisation with a procedures library."
- `mls-spatial-viewer` — "An interactive Leaflet web map that visualises cadastral search results. Live demo available."

---

## Notes for Discussion with James

The following should be discussed and may change this plan:

1. **Week order** — are there things James wants to tackle first or last?
2. **Technology choices** — any strong preferences on tools, languages, or frameworks?
3. **Career direction** — which industries is James most interested in? This should influence what gets prioritised.
4. **AutoCAD add-in (Week 6)** — if James decides he is not targeting AEC, Week 6 could instead be spent making the RAG assistant more polished (multi-document support, deployment, better UI) or adding QGIS plugin work.
5. **His own ideas** — what features or projects would James add to this plan?

---

*Draft: June 2026 | Mitchell Land Surveyors Pty Ltd*
