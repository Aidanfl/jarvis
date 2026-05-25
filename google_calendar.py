"""
JARVIS Google Calendar Access — read events directly from the Google Calendar API.

Used INSTEAD of the Apple Calendar / AppleScript path when configured, i.e. when
both credentials.json (OAuth client) and token.json (authorized user token) are
present in this directory. Read-only.

Setup:
  1. Create OAuth "Desktop app" credentials in Google Cloud, save as credentials.json here.
  2. Run `python google_calendar.py` once to authorize (opens a browser, writes token.json).
"""
import asyncio
import datetime
import logging
from pathlib import Path

log = logging.getLogger("jarvis.gcal")

_DIR = Path(__file__).parent
CREDS_FILE = _DIR / "credentials.json"
TOKEN_FILE = _DIR / "token.json"
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def is_enabled() -> bool:
    """True when Google Calendar is configured (OAuth client + an authorized token)."""
    return CREDS_FILE.exists() and TOKEN_FILE.exists()


def _load_creds():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json())
    return creds


def _fetch_todays_events_sync() -> list[dict]:
    from googleapiclient.discovery import build
    creds = _load_creds()
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)

    now = datetime.datetime.now().astimezone()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + datetime.timedelta(days=1)
    time_min, time_max = start.isoformat(), end.isoformat()

    out: list[dict] = []
    cals = service.calendarList().list().execute().get("items", [])
    for cal in cals:
        if cal.get("selected") is False:
            continue  # skip calendars the user has hidden
        cal_id = cal["id"]
        cal_name = cal.get("summaryOverride") or cal.get("summary", cal_id)
        try:
            resp = service.events().list(
                calendarId=cal_id, timeMin=time_min, timeMax=time_max,
                singleEvents=True, orderBy="startTime",
            ).execute()
        except Exception as e:
            log.debug(f"gcal list failed for {cal_name}: {e}")
            continue
        for ev in resp.get("items", []):
            s = ev.get("start", {})
            if "date" in s:  # all-day event
                start_dt = datetime.datetime.fromisoformat(s["date"])
                time_str, all_day = "ALL_DAY", True
            elif "dateTime" in s:
                # Normalize to naive local time to match the rest of the app.
                start_dt = datetime.datetime.fromisoformat(s["dateTime"]).astimezone().replace(tzinfo=None)
                time_str, all_day = start_dt.strftime("%-I:%M %p"), False
            else:
                continue
            out.append({
                "calendar": cal_name,
                "title": ev.get("summary", "(no title)"),
                "start": time_str,
                "start_dt": start_dt,
                "all_day": all_day,
            })
    out.sort(key=lambda e: (not e["all_day"], e.get("start_dt") or datetime.datetime.max))
    log.info(f"Google Calendar: {len(out)} events today across {len(cals)} calendars")
    return out


async def fetch_todays_events() -> list[dict]:
    """Async wrapper — runs the blocking Google API calls in a worker thread."""
    return await asyncio.to_thread(_fetch_todays_events_sync)


def authorize():
    """One-time interactive OAuth consent. Opens a browser, writes token.json."""
    from google_auth_oauthlib.flow import InstalledAppFlow
    if not CREDS_FILE.exists():
        raise SystemExit(f"Missing {CREDS_FILE} — download OAuth Desktop credentials first.")
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
    creds = flow.run_local_server(port=0)
    TOKEN_FILE.write_text(creds.to_json())
    print(f"Authorized. Token saved to {TOKEN_FILE}")


if __name__ == "__main__":
    authorize()
