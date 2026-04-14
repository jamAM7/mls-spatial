# THIS IS NOT USED, JUST TAKING LOGIC FROM IT TO USE IN drive.py.
# THIS IS OLD CODE FROM STEPHENS ORIGINAL PROJECT












#!/usr/bin/env python3
"""
drive_plans_fetch.py

Fetch cadastral plan references from NSW SIX Maps (ArcGIS), then search a Google Drive
(including Shared Drives / "shared with me") for matching plan PDFs/images, and download
ONLY the best/latest file per plan into ./plans/.

Selection rules (per planlabel):
1) Prefer PDF (application/pdf)
2) Prefer names containing "DP"
3) Prefer stronger match:
   - name contains exact "DP574558" (planlabel) beats name containing just digits "574558"
4) Prefer newest modifiedTime
5) Tie-breaker: larger size (if available), then name

Setup (once):
- Enable Google Drive API, create OAuth Desktop client, download credentials.json.
- pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib requests
- Put credentials.json next to this script and run once to create token.json.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, Optional
from datetime import datetime, timezone

# --- Your existing ArcGIS code (keep cadastral_records.py in same directory) ---
from cadastral_records import arcgis_query, LOT_LAYER  # type: ignore

# --- Google Drive API ---
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


# -----------------------------
# USER CONFIG
# -----------------------------
# BEST option (fast + reliable): if you know the folder containing plans, set this.
# Can be a folder in "My Drive" or a Shared Drive or a shared folder you have access to.
SEARCH_FOLDER_ID: Optional[str] = None

# Optional: if the plans are on a Shared Drive and you know its driveId, set it.
# If unknown, leave None (it will still search what the account can see).
DRIVE_ID: Optional[str] = None

DEST_DIR = Path("plans")

ALLOWED_MIME_PREFIXES = ("application/pdf", "image/")  # allow pdf + common image types

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


# -----------------------------
# Helpers
# -----------------------------
def safe_filename(name: str) -> str:
    name = name.replace("/", "-").replace("\\", "-").strip()
    name = re.sub(r"\s+", " ", name)
    return name


def parse_rfc3339(dt: str) -> datetime:
    # Drive gives e.g. "2024-10-01T02:03:04.123Z"
    # Python fromisoformat wants "+00:00" not "Z"
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


# -----------------------------
# ArcGIS: get nearby planlabels
# -----------------------------
def get_nearby_planlabels(lot_no: str, planlabel: str, buffer_m: float = 20.0) -> set[str]:
    """
    Returns planlabels near the target lot by intersecting the target polygon and a buffer.
    Includes the target planlabel itself.
    """
    lot_no = str(lot_no).strip()
    planlabel = str(planlabel).strip().upper()

    where = f"planlabel = '{planlabel}' AND lotnumber = '{lot_no}'"
    target = arcgis_query(LOT_LAYER, {
        "where": where,
        "outFields": "lotnumber,planlabel",
        "returnGeometry": "true",
        "outSR": "3857",
    })

    feats = target.get("features") or []
    if not feats:
        raise RuntimeError(f"Target lot not found: Lot {lot_no} {planlabel}")

    geom = (feats[0].get("geometry") or {})
    rings = geom.get("rings")
    if not rings:
        raise RuntimeError("Target feature returned without polygon rings.")

    poly = {"rings": rings, "spatialReference": {"wkid": 3857}}

    nearby = arcgis_query(LOT_LAYER, {
        "where": "1=1",
        "geometry": json.dumps(poly),
        "geometryType": "esriGeometryPolygon",
        "inSR": 3857,
        "spatialRel": "esriSpatialRelIntersects",
        "distance": buffer_m,
        "units": "esriSRUnit_Meter",
        "outFields": "lotnumber,planlabel,sectionnumber",
        "returnGeometry": "false",
    }, method="POST")

    planlabels = {planlabel}
    for f in (nearby.get("features") or []):
        a = f.get("attributes") or {}
        pl = (a.get("planlabel") or "").strip().upper()
        if pl:
            planlabels.add(pl)

    return planlabels


# -----------------------------
# Google Drive auth + helpers
# -----------------------------
def get_drive_service():
    """
    Creates an authenticated Drive API service, caching OAuth tokens in token.json.
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
                    "Missing credentials.json. Download OAuth Desktop client secrets and place "
                    "credentials.json next to this script."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return build("drive", "v3", credentials=creds)


def drive_list_files(service, q: str, page_size: int = 200) -> list[dict]:
    """
    List files matching a query, supporting shared drives.
    """
    files: list[dict] = []
    page_token = None

    base_kwargs = dict(
        q=q,
        fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, parents, driveId)",
        pageSize=page_size,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    )

    # If you know the Shared Drive ID, this can reduce scope.
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
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


# -----------------------------
# Drive query + selection logic
# -----------------------------
def build_drive_query_for_plan(planlabel: str) -> str:
    """
    Drive query:
    - name contains planlabel or just digits
    - mimeType pdf or image/*
    - optionally restrict to folder
    """
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


def choose_best_candidate(planlabel: str, candidates: list[dict]) -> Optional[dict]:
    """
    Pick ONE best file for this planlabel using the rules.
    Also EXCLUDES files containing '88b' in the name.
    """
    pl_exact, digits = plan_name_patterns(planlabel)

    # NEW: filter out names containing 88b
    filtered = []
    for f in candidates:
        name = (f.get("name") or "")
        if "88b" in name.lower():
            print(f"  [skip 88b] {name}")
            continue
        filtered.append(f)

    if not filtered:
        print("  [info] all candidates skipped due to 88b rule")
        return None

    def score(f: dict):
        name_u = (f.get("name") or "").upper()
        mime = (f.get("mimeType") or "").lower()

        is_pdf = 1 if mime == "application/pdf" else 0
        has_dp = 1 if "DP" in name_u else 0

        # match strength
        match_strength = 0
        if pl_exact and pl_exact in name_u:
            match_strength = 2
        elif digits and digits in name_u:
            match_strength = 1

        mtime = parse_rfc3339(f.get("modifiedTime") or "")
        size = int(f.get("size") or 0)

        return (
            is_pdf,
            has_dp,
            match_strength,
            mtime.timestamp(),
            size,
            name_u,
        )

    return max(filtered, key=score)


def build_drive_query_for_plan_xml(planlabel: str) -> str:
    """
    Drive query for XML sidecars:
    - name contains planlabel or digits
    - must be XML (mimeType contains 'xml' OR name contains '.xml')
    """
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


def choose_best_xml_candidate(planlabel: str, candidates: list[dict]) -> Optional[dict]:
    """
    Pick ONE best XML file for this planlabel.
    Rule: prefer .xml name, then newest modifiedTime, then largest size.
    Applies same '88b' skip rule as PDFs.
    """
    filtered = []
    for f in candidates:
        name = (f.get("name") or "")
        if "88b" in name.lower():
            print(f"  [skip 88b] {name}")
            continue
        filtered.append(f)

    if not filtered:
        return None

    def score(f: dict):
        name = (f.get("name") or "")
        name_l = name.lower()
        mime = (f.get("mimeType") or "").lower()

        ends_xml = 1 if name_l.endswith(".xml") else 0
        mime_xml = 1 if "xml" in mime else 0

        mtime = parse_rfc3339(f.get("modifiedTime") or "")
        size = int(f.get("size") or 0)

        return (
            ends_xml,
            mime_xml,
            mtime.timestamp(),
            size,
            name_l,
        )

    return max(filtered, key=score)


def fetch_plans_from_drive(planlabels: Iterable[str]) -> list[Path]:
    """
    For each planlabel: search Drive, choose BEST match, download into DEST_DIR.
    Returns list of downloaded file paths.
    """
    service = get_drive_service()
    downloaded: list[Path] = []

    for pl in sorted({p.strip().upper() for p in planlabels if p and p.strip()}):
        q = build_drive_query_for_plan(pl)
        hits = drive_list_files(service, q=q)

        # de-dupe by file id
        uniq = {}
        for h in hits:
            if h.get("id"):
                uniq[h["id"]] = h
        hits = list(uniq.values())

        print(f"\n[Drive] {pl}: {len(hits)} candidate(s)")
        if not hits:
            continue

        # ---- A) Pick + download best PDF/image (existing behaviour) ----
        best = choose_best_candidate(pl, hits)
        if best:
            best_name = best.get("name", "")
            best_mime = best.get("mimeType", "")
            best_time = best.get("modifiedTime", "")
            print(f"  [pick] {best_mime} | {best_time} | {best_name}")

            out_name = safe_filename(best_name)
            out_path = DEST_DIR / out_name

            download_file(service, best["id"], out_path)
            downloaded.append(out_path)
        else:
            print("  [info] no suitable PDF/image candidate found")

        # ---- B) ALSO find + download XML sidecar (new behaviour) ----
        q_xml = build_drive_query_for_plan_xml(pl)
        hits_xml = drive_list_files(service, q=q_xml)

        # de-dupe by file id
        uniq_xml = {}
        for h in hits_xml:
            if h.get("id"):
                uniq_xml[h["id"]] = h
        hits_xml = list(uniq_xml.values())

        print(f"  [xml] {pl}: {len(hits_xml)} candidate(s)")
        if hits_xml:
            best_xml = choose_best_xml_candidate(pl, hits_xml)
            if best_xml:
                xml_name = best_xml.get("name", "")
                xml_time = best_xml.get("modifiedTime", "")
                print(f"  [pick xml] {xml_time} | {xml_name}")

                out_xml = DEST_DIR / safe_filename(xml_name)
                download_file(service, best_xml["id"], out_xml)
                downloaded.append(out_xml)


    return downloaded


# -----------------------------
# Main
# -----------------------------
def main():
    # Example target (change these)
    lot_no = "102"
    planlabel = "DP574558"
    buffer_m = 20.0

    print(f"Target: Lot {lot_no} {planlabel}")

    planlabels = get_nearby_planlabels(lot_no, planlabel, buffer_m=buffer_m)
    print(f"Planlabels found from cadastre: {len(planlabels)}")
    for p in sorted(planlabels):
        print("  ", p)

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = fetch_plans_from_drive(planlabels)

    print(f"\nDone. Downloaded {len(downloaded)} file(s) into: {DEST_DIR.resolve()}")
    if downloaded:
        print("Example:")
        print(" ", downloaded[0])


if __name__ == "__main__":
    main()
