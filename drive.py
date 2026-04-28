"""
drive.py — MLS Spatial Search Service
Google Drive plan search and download.

Ported from Stephen's MLS_Plan_Searcher project (drive_plans_fetch.py).

Setup (once):
- Enable Google Drive API, create OAuth Desktop client, download credentials.json.
- pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
- Place credentials.json in the project root and run once to create token.json.

credentials.json and token.json are gitignored — never commit them.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Iterable
from datetime import datetime, timezone

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from models import SearchResult


# ── Config ────────────────────────────────────────────────────────────────────

# If you know the Google Drive folder ID containing plans, set this.
# Leave None to search all files the account can see.
SEARCH_FOLDER_ID: Optional[str] = None

# If plans are on a Shared Drive and you know its driveId, set this.
DRIVE_ID: Optional[str] = None

ALLOWED_MIME_PREFIXES = ("application/pdf", "image/")

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def safe_filename(name: str) -> str:
    name = name.replace("/", "-").replace("\\", "-").strip()
    name = re.sub(r"\s+", " ", name)
    return name


def parse_rfc3339(dt: str) -> datetime:
    if not dt:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    dt = dt.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(dt)
    except ValueError:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)


def plan_name_patterns(planlabel: str) -> tuple[str, str]:
    """
    Returns (PL_EXACT, DIGITS) for matching.
    Example: "DP574558" -> ("DP574558", "574558")
    """
    pl = planlabel.strip().upper()
    digits = re.sub(r"[^0-9]", "", pl)
    return pl, digits


# ── Google Drive auth ─────────────────────────────────────────────────────────

def get_drive_service():
    """
    Creates an authenticated Drive API service.
    Caches OAuth tokens in token.json.
    On first run, opens a browser window to authenticate.
    """
    creds: Optional[Credentials] = None
    token_path = Path("token.json")
    creds_path = Path("credentials.json")

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not creds_path.exists():
                raise FileNotFoundError(
                    "Missing credentials.json. Download OAuth Desktop client secrets "
                    "from Google Cloud Console and place in the project root."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return build("drive", "v3", credentials=creds)


# ── Drive query helpers ───────────────────────────────────────────────────────

def drive_list_files(service, q: str, page_size: int = 200) -> list[dict]:
    """List files matching a Drive query, supporting shared drives."""
    files: list[dict] = []
    page_token = None

    base_kwargs = dict(
        q=q,
        fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, parents, driveId)",
        pageSize=page_size,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    )

    if DRIVE_ID:
        base_kwargs["corpora"] = "drive"
        base_kwargs["driveId"] = DRIVE_ID
    else:
        base_kwargs["corpora"] = "user"

    while True:
        resp = service.files().list(pageToken=page_token, **base_kwargs).execute()
        files.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return files


def download_file(service, file_id: str, out_path: Path) -> None:
    """Download a Drive file to out_path."""
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


# ── File selection logic ──────────────────────────────────────────────────────

def build_drive_query_for_plan(planlabel: str) -> str:
    """Builds a Drive search query for a plan PDF or image."""
    pl_exact, digits = plan_name_patterns(planlabel)

    name_parts = [f"name contains '{pl_exact}'"]
    if digits and digits != pl_exact:
        name_parts.append(f"name contains '{digits}'")
    name_expr = " OR ".join(name_parts)

    mime_expr = " OR ".join([f"mimeType contains '{p}'" for p in ALLOWED_MIME_PREFIXES])

    q = f"trashed = false AND ({name_expr}) AND ({mime_expr})"
    if SEARCH_FOLDER_ID:
        q += f" AND '{SEARCH_FOLDER_ID}' in parents"

    return q


def build_drive_query_for_plan_xml(planlabel: str) -> str:
    """Builds a Drive search query for an XML sidecar file."""
    pl_exact, digits = plan_name_patterns(planlabel)

    name_parts = [f"name contains '{pl_exact}'"]
    if digits and digits != pl_exact:
        name_parts.append(f"name contains '{digits}'")
    name_expr = " OR ".join(name_parts)

    xml_expr = "(mimeType contains 'xml' OR name contains '.xml')"

    q = f"trashed = false AND ({name_expr}) AND {xml_expr}"
    if SEARCH_FOLDER_ID:
        q += f" AND '{SEARCH_FOLDER_ID}' in parents"
    return q


def _is_exact_plan_match(filename: str, pl_exact: str, digits: str) -> bool:
    """
    Returns True only if the filename contains the plan label as a whole token.
    e.g. "DP123554" matches "DP123554.pdf" but NOT "DP1235542.pdf"
    Also matches "Deposited Plan 123554" but not SP plans.
    """
    name_u = filename.upper()

    # Must not be an SP plan
    if re.search(r'\bSP\s*' + digits, name_u):
        return False

    # Exact label match as whole word e.g. "DP123554"
    if re.search(r'\b' + re.escape(pl_exact) + r'\b', name_u):
        return True

    # "DP_123554" or "DP 123554"
    if re.search(r'\bDP[\s_]0*' + digits + r'\b', name_u):
        return True

    # "Deposited Plan 123554"
    if re.search(r'DEPOSITED[\s_]PLAN[\s_]0*' + digits + r'\b', name_u):
        return True

    return False


# def choose_best_candidate(planlabel: str, candidates: list[dict]) -> Optional[dict]:
#     """
#     Pick the best PDF/image file for a plan.
#     Rules: prefer PDF > has DP in name > exact label match > newest > largest
#     Skips files containing '88b' in the name.
#     """
#     pl_exact, digits = plan_name_patterns(planlabel)

#     filtered = []
#     for f in candidates:
#         name = f.get("name") or ""
#         if "88b" in name.lower():
#             print(f"  [skip 88b] {name}")
#             continue
#         filtered.append(f)

#     if not filtered:
#         return None

#     def score(f: dict):
#         name_u = (f.get("name") or "").upper()
#         mime = (f.get("mimeType") or "").lower()

#         is_pdf = 1 if mime == "application/pdf" else 0
#         has_dp = 1 if "DP" in name_u else 0

#         # match_strength = 0
#         # if pl_exact and pl_exact in name_u:
#         #     match_strength = 2
#         # elif digits and digits in name_u:
#         #     match_strength = 1

#         if not _is_exact_plan_match(f.get("name", ""), pl_exact, digits):
#             continue  # skip files that don't exactly match this plan
#         match_strength = 2

#         mtime = parse_rfc3339(f.get("modifiedTime") or "")
#         size = int(f.get("size") or 0)

#         return (is_pdf, has_dp, match_strength, mtime.timestamp(), size, name_u)

#     return max(filtered, key=score)

def choose_best_candidate(planlabel: str, candidates: list[dict]) -> Optional[dict]:
    pl_exact, digits = plan_name_patterns(planlabel)

    filtered = []
    for f in candidates:
        name = f.get("name") or ""
        print(f"  [checking] {name}")  # THIS IS A TEMPORARY CHECK
        # Skip 88b files
        if "88b" in name.lower():
            print(f"  [skip 88b] {name}")
            continue
        # Skip files that don't exactly match this plan
        if not _is_exact_plan_match(name, pl_exact, digits):
            print(f"  [skip no match] {name}")
            continue
        filtered.append(f)

    if not filtered:
        return None

    def score(f: dict):
        name_u = (f.get("name") or "").upper()
        mime = (f.get("mimeType") or "").lower()
        is_pdf = 1 if mime == "application/pdf" else 0
        has_dp = 1 if "DP" in name_u else 0
        mtime = parse_rfc3339(f.get("modifiedTime") or "")
        size = int(f.get("size") or 0)
        return (is_pdf, has_dp, 2, mtime.timestamp(), size, name_u)

    return max(filtered, key=score)


# def choose_best_xml_candidate(planlabel: str, candidates: list[dict]) -> Optional[dict]:
#     """Pick the best XML sidecar file for a plan."""
#     filtered = []
#     for f in candidates:
#         name = f.get("name") or ""
#         if "88b" in name.lower():
#             print(f"  [skip 88b] {name}")
#             continue
#         filtered.append(f)

#     if not filtered:
#         return None

#     def score(f: dict):
#         name_l = (f.get("name") or "").lower()
#         mime = (f.get("mimeType") or "").lower()
#         ends_xml = 1 if name_l.endswith(".xml") else 0
#         mime_xml = 1 if "xml" in mime else 0
#         mtime = parse_rfc3339(f.get("modifiedTime") or "")
#         size = int(f.get("size") or 0)
#         return (ends_xml, mime_xml, mtime.timestamp(), size, name_l)

#     return max(filtered, key=score)

def choose_best_xml_candidate(planlabel: str, candidates: list[dict]) -> Optional[dict]:
    pl_exact, digits = plan_name_patterns(planlabel)
    
    filtered = []
    for f in candidates:
        name = f.get("name") or ""
        if "88b" in name.lower():
            print(f"  [skip 88b] {name}")
            continue
        if not _is_exact_plan_match(name, pl_exact, digits):
            print(f"  [skip no match] {name}")
            continue
        filtered.append(f)

    if not filtered:
        return None

    def score(f: dict):
        name_l = (f.get("name") or "").lower()
        mime = (f.get("mimeType") or "").lower()
        ends_xml = 1 if name_l.endswith(".xml") else 0
        mime_xml = 1 if "xml" in mime else 0
        mtime = parse_rfc3339(f.get("modifiedTime") or "")
        size = int(f.get("size") or 0)
        return (ends_xml, mime_xml, mtime.timestamp(), size, name_l)

    return max(filtered, key=score)


# ── Main entry point ──────────────────────────────────────────────────────────

def download_plans(result: SearchResult, dest_folder: Path) -> SearchResult:
    """
    For each Plan in result.plans, search Google Drive for a matching PDF or image.
    Download the best match to dest_folder/plans/.
    Returns the same SearchResult with local_file set on each Plan that was found.
    Downloads both PDF/image and XML sidecar where available.
    """
    service = get_drive_service()
    plans_folder = dest_folder / "plans"
    plans_folder.mkdir(parents=True, exist_ok=True)

    for plan in result.plans:
        # Search for PDF/image
        q = build_drive_query_for_plan(plan.plan_label)
        hits = drive_list_files(service, q=q)
        uniq = {h["id"]: h for h in hits if h.get("id")}
        hits = list(uniq.values())

        print(f"[Drive] {plan.plan_label}: {len(hits)} candidate(s)")

        best = choose_best_candidate(plan.plan_label, hits)
        if best:
            out_path = plans_folder / safe_filename(best.get("name", ""))
            download_file(service, best["id"], out_path)
            plan.local_file = out_path
            print(f"  [downloaded] {out_path.name}")

        # Also search for XML sidecar
        q_xml = build_drive_query_for_plan_xml(plan.plan_label)
        hits_xml = drive_list_files(service, q=q_xml)
        uniq_xml = {h["id"]: h for h in hits_xml if h.get("id")}
        hits_xml = list(uniq_xml.values())

        if hits_xml:
            best_xml = choose_best_xml_candidate(plan.plan_label, hits_xml)
            if best_xml:
                out_xml = plans_folder / safe_filename(best_xml.get("name", ""))
                download_file(service, best_xml["id"], out_xml)
                print(f"  [downloaded xml] {out_xml.name}")

    return result