"""
MapleStory ranking → CSV → R2 for GitHub Actions / headless servers.

"""

import csv
import logging
import os
import re
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

import boto3
import requests
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

# Populated by configure_runtime()
DATA_DIR = Path(__file__).resolve().parent
R2_BUCKET: Optional[str] = None
R2_ACCESS_KEY_ID: Optional[str] = None
R2_SECRET_ACCESS_KEY: Optional[str] = None
R2_ENDPOINT: Optional[str] = None
R2_UPLOAD_DAILY_NAME = ""
R2_UPLOAD_WEEK_NAME = ""
R2_UPLOAD_MONTH_NAME = ""
MAPLE_RANKING_API_URL = ""
MAPLE_REBOOT_INDEX = 0
MY_CHARACTERS: List[str] = []
MAPLE_JOB_LABEL = ""
s3_client = None

# EXP table for level calculations
EXP_TABLE = {
  1: 15, 2: 34, 3: 57, 4: 92, 5: 135, 6: 372, 7: 560, 8: 840, 9: 1242, 10: 1242,
  11: 1242, 12: 1242, 13: 1242, 14: 1242, 15: 1490, 16: 1788, 17: 2145, 18: 2574,
  19: 3088, 20: 3705, 21: 4446, 22: 5335, 23: 6402, 24: 7682, 25: 9218, 26: 11061,
  27: 13273, 28: 15927, 29: 19112, 30: 19112, 31: 19112, 32: 19112, 33: 19112,
  34: 19112, 35: 22934, 36: 27520, 37: 33024, 38: 39628, 39: 47553, 40: 51357,
  41: 55465, 42: 59902, 43: 64694, 44: 69869, 45: 75458, 46: 81494, 47: 88013,
  48: 95054, 49: 102658, 50: 110870, 51: 119739, 52: 129318, 53: 139663, 54: 150836,
  55: 162902, 56: 175934, 57: 190008, 58: 205208, 59: 221624, 60: 221624, 61: 221624,
  62: 221624, 63: 221624, 64: 221624, 65: 238245, 66: 256113, 67: 275321, 68: 295970,
  69: 318167, 70: 342029, 71: 367681, 72: 395257, 73: 424901, 74: 456768, 75: 488741,
  76: 522952, 77: 559558, 78: 598727, 79: 640637, 80: 685481, 81: 733464, 82: 784806,
  83: 839742, 84: 898523, 85: 961419, 86: 1028718, 87: 1100728, 88: 1177778, 89: 1260222,
  90: 1342136, 91: 1429374, 92: 1522283, 93: 1621231, 94: 1726611, 95: 1838840, 96: 1958364,
  97: 2085657, 98: 2221224, 99: 2365603, 100: 2365603, 101: 2365603, 102: 2365603,
  103: 2365603, 104: 2365603, 105: 2519367, 106: 2683125, 107: 2857528, 108: 3043267,
  109: 3241079, 110: 3451749, 111: 3676112, 112: 3915059, 113: 4169537, 114: 4440556,
  115: 4729192, 116: 5036589, 117: 5363967, 118: 5712624, 119: 6083944, 120: 6479400,
  121: 6900561, 122: 7349097, 123: 7826788, 124: 8335529, 125: 8877338, 126: 9454364,
  127: 10068897, 128: 10723375, 129: 11420394, 130: 12162719, 131: 12953295, 132: 13795259,
  133: 14691950, 134: 15646926, 135: 16663976, 136: 17747134, 137: 18900697, 138: 20129242,
  139: 21437642, 140: 22777494, 141: 24201087, 142: 25713654, 143: 27320757, 144: 29028304,
  145: 30842573, 146: 32770233, 147: 34818372, 148: 36994520, 149: 39306677, 150: 41763344,
  151: 44373553, 152: 47146900, 153: 50093581, 154: 53224429, 155: 56550955, 156: 60085389,
  157: 63840725, 158: 67830770, 159: 72070193, 160: 76574580, 161: 81360491, 162: 86445521,
  163: 91848366, 164: 97588888, 165: 103688193, 166: 110168705, 167: 117054249, 168: 124370139,
  169: 132143272, 170: 138750435, 171: 145687956, 172: 152972353, 173: 160620970,
  174: 168652018, 175: 177084618, 176: 185938848, 177: 195235790, 178: 204997579,
  179: 215247457, 180: 226009829, 181: 237310320, 182: 249175836, 183: 261634627,
  184: 274716358, 185: 288452175, 186: 302874783, 187: 318018522, 188: 333919448,
  189: 350615420, 190: 368146191, 191: 386553500, 192: 405881175, 193: 426175233,
  194: 447483994, 195: 469858193, 196: 493351102, 197: 518018657, 198: 543919589,
  199: 571115568, 200: 2207026470, 201: 2471869646, 202: 2768494003, 203: 3100713283,
  204: 3472798876, 205: 3889534741, 206: 4356278909, 207: 4879032378, 208: 5464516263,
  209: 6120258214, 210: 7956335678, 211: 8831532602, 212: 9803001188, 213: 10881331318,
  214: 12078277762, 215: 15701761090, 216: 17114919588, 217: 18655262350, 218: 20334235961,
  219: 22164317197, 220: 28813612356, 221: 30830565220, 222: 32988704785, 223: 35297914119,
  224: 37768768107, 225: 49099398539, 226: 52536356436, 227: 56213901386, 228: 60148874483,
  229: 64359295696, 230: 83667084404, 231: 86177096936, 232: 88762409844, 233: 91425282139,
  234: 94168040603, 235: 122418452783, 236: 126091006366, 237: 129873736556, 238: 133769948652,
  239: 137783047111, 240: 179117961244, 241: 184491500081, 242: 190026245083, 243: 195727032435,
  244: 201598843408, 245: 262078496430, 246: 269940851322, 247: 278039076861, 248: 286380249166,
  249: 294971656640, 250: 442457484960, 251: 455731209508, 252: 469403145793, 253: 483485240166,
  254: 497989797370, 255: 512929491291, 256: 528317376029, 257: 544166897309, 258: 560491904228,
  259: 577306661354, 260: 1731919984062, 261: 1749239183902, 262: 1766731575741,
  263: 1784398891498, 264: 1802242880412, 265: 2342915744535, 266: 2366344901980,
  267: 2390008350999, 268: 2413908434508, 269: 2438047518853, 270: 5412465491853,
  271: 5466590146771, 272: 5521256048238, 273: 5576468608720, 274: 5632233294807,
  275: 11377111255510, 276: 12514822381061, 277: 13766304619167, 278: 15142935081083,
  279: 16657228589191, 280: 33647601750165, 281: 37012361925181, 282: 40713598117699,
  283: 44784957929468, 284: 49263453722414, 285: 99512176519276, 286: 109463394171203,
  287: 120409733588323, 288: 132450706947155, 289: 145695777641870, 290: 294305470836577,
  291: 323736017920234, 292: 356109619712257, 293: 391720581683483, 294: 430892639851831,
  295: 870403132500699, 296: 957443445750769, 297: 1053187790325840, 298: 1158506569358420,
  299: 1737759854037630, 300: None
}


def _parse_my_characters(raw: str) -> List[str]:
    parts = re.split(r"[;,]", raw)
    return [p.strip() for p in parts if p.strip()]


def configure_runtime() -> None:
    """Load env into module globals. Call once before any R2 or fetch logic."""
    global R2_BUCKET, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT
    global R2_UPLOAD_DAILY_NAME, R2_UPLOAD_WEEK_NAME, R2_UPLOAD_MONTH_NAME
    global MAPLE_RANKING_API_URL, MAPLE_REBOOT_INDEX, MY_CHARACTERS, MAPLE_JOB_LABEL
    global s3_client

    R2_BUCKET = os.getenv("R2_BUCKET")
    R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
    R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
    R2_ENDPOINT = os.getenv("R2_ENDPOINT")
    R2_UPLOAD_DAILY_NAME = (os.getenv("R2_UPLOAD_DAILY_NAME") or "").strip()
    R2_UPLOAD_WEEK_NAME = (os.getenv("R2_UPLOAD_WEEK_NAME") or "").strip()
    R2_UPLOAD_MONTH_NAME = (os.getenv("R2_UPLOAD_MONTH_NAME") or "").strip()
    missing_obj = [
        n
        for n, v in (
            ("R2_UPLOAD_DAILY_NAME", R2_UPLOAD_DAILY_NAME),
            ("R2_UPLOAD_WEEK_NAME", R2_UPLOAD_WEEK_NAME),
            ("R2_UPLOAD_MONTH_NAME", R2_UPLOAD_MONTH_NAME),
        )
        if not v
    ]
    if missing_obj:
        print(
            "Set non-empty R2 object key names for daily, weekly, and monthly CSVs "
            "(see env var names printed below).",
            file=sys.stderr,
        )
        print("Missing: " + ", ".join(missing_obj), file=sys.stderr)
        sys.exit(1)

    MAPLE_RANKING_API_URL = (os.getenv("MAPLE_RANKING_API_URL") or "").strip()
    if not MAPLE_RANKING_API_URL:
        print("MAPLE_RANKING_API_URL must be set to the ranking API base URL.", file=sys.stderr)
        sys.exit(1)
    MAPLE_REBOOT_INDEX = int((os.getenv("MAPLE_REBOOT_INDEX") or "0").strip() or "0")
    MAPLE_JOB_LABEL = (os.getenv("MAPLE_JOB_LABEL") or "").strip()

    raw_chars = (os.getenv("MY_CHARACTERS") or "").strip()
    MY_CHARACTERS[:] = _parse_my_characters(raw_chars)
    if not MY_CHARACTERS:
        print("MY_CHARACTERS is empty or missing. Set semicolon/comma-separated values.", file=sys.stderr)
        sys.exit(1)

    missing_r2 = [
        n
        for n, v in (
            ("R2_BUCKET", R2_BUCKET),
            ("R2_ACCESS_KEY_ID", R2_ACCESS_KEY_ID),
            ("R2_SECRET_ACCESS_KEY", R2_SECRET_ACCESS_KEY),
            ("R2_ENDPOINT", R2_ENDPOINT),
        )
        if not v
    ]
    if missing_r2:
        print("Missing required R2 environment variables: " + ", ".join(missing_r2), file=sys.stderr)
        sys.exit(1)

    s3_client = boto3.client(
        "s3",
        region_name="auto",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    )
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def r2_download_daily_or_exit(local_dir: Path) -> None:
    """Daily CSV must exist in R2. Missing object or transport error → exit."""
    assert s3_client is not None
    dest = local_dir / R2_UPLOAD_DAILY_NAME
    local_dir.mkdir(parents=True, exist_ok=True)
    try:
        s3_client.download_file(R2_BUCKET, R2_UPLOAD_DAILY_NAME, str(dest))
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            print(
                "R2: daily CSV object missing. Upload a bootstrap file for the configured "
                "daily object key, then re-run.",
                file=sys.stderr,
            )
        else:
            print("R2: daily CSV download failed (see Discord for details if configured).", file=sys.stderr)
        sys.exit(1)
    except OSError:
        print("R2: could not write daily CSV to local data directory.", file=sys.stderr)
        sys.exit(1)


def r2_download_optional_week_month(local_dir: Path) -> None:
    """Weekly/monthly objects are optional; missing keys are ignored."""
    assert s3_client is not None
    local_dir.mkdir(parents=True, exist_ok=True)
    for key, label in (
        (R2_UPLOAD_WEEK_NAME, "weekly"),
        (R2_UPLOAD_MONTH_NAME, "monthly"),
    ):
        dest = local_dir / key
        try:
            s3_client.download_file(R2_BUCKET, key, str(dest))
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("404", "NoSuchKey"):
                if dest.exists():
                    dest.unlink(missing_ok=True)
                print(f"R2: no existing {label} CSV — will rebuild from daily if possible.")
            else:
                print(
                    f"R2: optional {label} download failed; continuing without that file.",
                    file=sys.stderr,
                )
        except OSError:
            print(
                "R2: optional weekly/monthly local write issue; continuing.",
                file=sys.stderr,
            )


DISCORD_MESSAGE_MAX_LEN = 2000


def _redact_sensitive_fragments(text: str) -> str:
    """
    Remove values that must not appear in Discord failure payloads (URLs, R2 credentials,
    values from MY_CHARACTERS, Discord webhook and numeric user id when echoed by libraries).
    """
    if not text:
        return text
    text = re.sub(r"(character_name=)[^&\s\"'>]+", r"\1<redacted>", text, flags=re.IGNORECASE)
    text = re.sub(r'(characterName["\']?\s*:\s*["\'])([^"\']+)', r"\1<redacted>", text, flags=re.IGNORECASE)
    for label, val in (
        ("R2_ENDPOINT", R2_ENDPOINT),
        ("R2_BUCKET", R2_BUCKET),
        ("R2_ACCESS_KEY_ID", R2_ACCESS_KEY_ID),
        ("R2_SECRET_ACCESS_KEY", R2_SECRET_ACCESS_KEY),
    ):
        if val and len(str(val)) > 3 and str(val) in text:
            text = text.replace(str(val), f"<{label}_redacted>")
    webhook = (os.getenv("DISCORD_WEBHOOK_URL") or os.getenv("DISCORD_WEBHOOK") or "").strip()
    if webhook and len(webhook) > 12 and webhook in text:
        text = text.replace(webhook, "<webhook_redacted>")
    uid = (os.getenv("DISCORD_USER_ID") or "").strip()
    if uid and uid in text:
        text = text.replace(uid, "<discord_user_redacted>")
    for name in sorted(MY_CHARACTERS, key=len, reverse=True):
        if len(name) >= 2 and name in text:
            text = text.replace(name, "<subject_redacted>")
    if MAPLE_RANKING_API_URL and len(MAPLE_RANKING_API_URL) > 8 and MAPLE_RANKING_API_URL in text:
        text = text.replace(MAPLE_RANKING_API_URL, "<ranking_api_url_redacted>")
    for fn in (R2_UPLOAD_DAILY_NAME, R2_UPLOAD_WEEK_NAME, R2_UPLOAD_MONTH_NAME):
        if fn and len(fn) > 1 and fn in text:
            text = text.replace(fn, "<r2_object_key_redacted>")
    return text


def format_failure_for_discord(mention: str, run_ts: int, exc: BaseException) -> str:
    header = f"{mention}MapleStory data (GitHub) failed at <t:{run_ts}:f>\n"
    exc_line = _redact_sensitive_fragments(f"{exc!s}")
    tb = _redact_sensitive_fragments(traceback.format_exc())
    body = f"{header}{exc_line}\n\n{tb}"
    if len(body) <= DISCORD_MESSAGE_MAX_LEN:
        return body
    prefix = f"{header}{exc_line}\n\n"
    room = DISCORD_MESSAGE_MAX_LEN - len(prefix) - 1
    if room < 1:
        return body[:DISCORD_MESSAGE_MAX_LEN]
    return prefix + tb[:room] + "…"


def send_discord_alert(message: str) -> None:
    webhook_url = (os.getenv("DISCORD_WEBHOOK_URL") or os.getenv("DISCORD_WEBHOOK") or "").strip()
    if not webhook_url:
        return
    try:
        requests.post(webhook_url, json={"content": message}, timeout=10)
    except Exception:
        print("Failed to send Discord notification.", file=sys.stderr)


def fetch_ranking_row(subject_name: str, reboot_index: int = 0) -> Optional[Dict]:
    """HTTP GET ranking API; returns one row dict or None."""
    try:
        url = MAPLE_RANKING_API_URL
        base_params = {
            "type": "overall",
            "id": "weekly",
            "reboot_index": reboot_index,
            "page_index": 1,
            "character_name": subject_name
        }
        
        response = requests.get(url, params=base_params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("ranks") or len(data["ranks"]) == 0:
            print("No ranking rows returned for one indexed lookup in this batch.")
            return None

        char_data = data["ranks"][0]

        achievement_data = requests.get(url, params={"type": "achievement", "page_index": 1, "character_name": subject_name}, timeout=10).json()
        fame_data = requests.get(url, params={"type": "fame", "id": "weekly", "reboot_index": reboot_index, "page_index": 1, "character_name": subject_name}, timeout=10).json()
        job_data = requests.get(url, params={"type": "job", "id": char_data["jobName"], "reboot_index": reboot_index, "page_index": 1, "character_name": subject_name}, timeout=10).json()
        legion_data = requests.get(url, params={"type": "legion", "id": char_data["worldID"], "page_index": 1, "character_name": subject_name}, timeout=10).json()
        world_data = requests.get(url, params={"type": "world", "id": char_data["worldID"], "reboot_index": reboot_index, "page_index": 1, "character_name": subject_name}, timeout=10).json()

        weekly_overall = requests.get(url, params={"type": "overall", "id": "weekly", "page_index": 1, "character_name": subject_name}, timeout=10).json()
        weekly_fame = requests.get(url, params={"type": "fame", "id": "weekly", "reboot_index": reboot_index, "page_index": 1, "character_name": subject_name}, timeout=10).json()

        monthly_overall = requests.get(url, params={"type": "overall", "id": "monthly", "page_index": 1, "character_name": subject_name}, timeout=10).json()
        monthly_fame = requests.get(url, params={"type": "fame", "id": "monthly", "reboot_index": reboot_index, "page_index": 1, "character_name": subject_name}, timeout=10).json()

        legendary_overall = requests.get(url, params={"type": "overall", "id": "legendary", "page_index": 1, "character_name": subject_name}, timeout=10).json()
        legendary_fame = requests.get(url, params={"type": "fame", "id": "legendary", "reboot_index": reboot_index, "page_index": 1, "character_name": subject_name}, timeout=10).json()

        def get_rank(response_data):
            return response_data["ranks"][0]["rank"] if response_data.get("ranks") else 0
        
        return {
            "character_name": char_data["characterName"],
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": char_data["level"],
            "current_level_exp": char_data["exp"],
            "overall_rank": char_data["rank"],
            "achievement_rank": get_rank(achievement_data),
            "achievement_score": achievement_data["ranks"][0].get("starSum", 0) if achievement_data.get("ranks") else 0,
            "fame_rank": get_rank(fame_data),
            "fame_points": fame_data["ranks"][0].get("exp", 0) if fame_data.get("ranks") else 0,
            "job_rank": get_rank(job_data),
            "legion_rank": get_rank(legion_data),
            "world_rank": get_rank(world_data),
            "job_name": char_data["jobName"],
            "world_id": char_data["worldID"],
            "character_image_url": char_data["characterImgURL"],
            "weekly_exp_gain": char_data.get("gap", 0),
            "weekly_overall_rank": get_rank(weekly_overall),
            "weekly_fame_rank": get_rank(weekly_fame),
            "monthly_overall_rank": get_rank(monthly_overall),
            "monthly_fame_rank": get_rank(monthly_fame),
            "legendary_overall_rank": get_rank(legendary_overall),
            "legendary_fame_rank": get_rank(legendary_fame),
        }
        
    except Exception as e:
        print(f"Ranking request failed ({type(e).__name__}). Check Discord for details if configured.")
        return None





def load_existing_csv(file_path: Path) -> List[Dict]:
    """Load existing CSV data."""
    if not file_path.exists():
        return []
    
    with open(file_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def calculate_weekly_aggregates(local_path: Path):
    """Calculate ISO week-based aggregates from daily data."""
    daily_csv_path = local_path / R2_UPLOAD_DAILY_NAME
    weekly_csv_path = local_path / R2_UPLOAD_WEEK_NAME
    daily_data = load_existing_csv(daily_csv_path)
    
    if not daily_data:
        print("⚠️ No daily data found for weekly aggregation")
        return
    
    # Group by stable row key and ISO week
    weekly_aggregates = {}
    for row in daily_data:
        char_name = row["character_name"]
        date_obj = datetime.strptime(row["date"], "%Y-%m-%d")
        iso_year, iso_week, _ = date_obj.isocalendar()
        week_key = f"{iso_year}-W{iso_week:02d}"
        key = (char_name, week_key)
        
        if key not in weekly_aggregates:
            weekly_aggregates[key] = {
                "character_name": char_name,
                "week": week_key,
                "level_start": int(row["level"]),
                "level_end": int(row["level"]),
                "first_level": int(row["level"]),
                "last_level": int(row["level"]),
                "first_level_exp": int(row.get("current_level_exp", 0)),
                "last_level_exp": int(row.get("current_level_exp", 0)),
                "dates": [row["date"]]
            }
        else:
            weekly_aggregates[key]["last_level"] = int(row["level"])
            weekly_aggregates[key]["last_level_exp"] = int(row.get("current_level_exp", 0))
            weekly_aggregates[key]["level_end"] = int(row["level"])
            weekly_aggregates[key]["dates"].append(row["date"])
    
    # Convert to list and calculate exp gain with level accounting
    weekly_rows = []
    for agg in weekly_aggregates.values():
        total_exp = 0
        
        # If same level, simple subtraction
        if agg["first_level"] == agg["last_level"]:
            total_exp = agg["last_level_exp"] - agg["first_level_exp"]
        else:
            # Level changed: add remaining exp from first level + all intermediate levels + current progress
            first_level = agg["first_level"]
            last_level = agg["last_level"]
            
            # EXP needed to complete first level
            if first_level < 300 and EXP_TABLE.get(first_level):
                total_exp += EXP_TABLE[first_level] - agg["first_level_exp"]
            
            # EXP from all completed intermediate levels
            for lvl in range(first_level + 1, last_level):
                if lvl < 300 and EXP_TABLE.get(lvl):
                    total_exp += EXP_TABLE[lvl]
            
            # Current progress on last level
            total_exp += agg["last_level_exp"]
        
        weekly_rows.append({
            "character_name": agg["character_name"],
            "week": agg["week"],
            "total_exp_gain": total_exp,
            "level_start": agg["first_level"],
            "level_end": agg["last_level"],
            "days_tracked": len(agg["dates"])
        })
    
    # Sort by week (newest first) then name column
    weekly_rows.sort(key=lambda x: (x["week"], x["character_name"]), reverse=True)
    
    # Keep only last 12 weeks of data
    cutoff_week_date = datetime.now(timezone.utc) - timedelta(weeks=12)
    cutoff_week = f"{cutoff_week_date.isocalendar()[0]}-W{cutoff_week_date.isocalendar()[1]:02d}"
    weekly_rows = [row for row in weekly_rows if row["week"] >= cutoff_week]
    
    if weekly_rows:
        fieldnames = ["character_name", "week", "total_exp_gain", "level_start", "level_end", "days_tracked"]
        with open(weekly_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(weekly_rows)
        print(f"✓ Saved {len(weekly_rows)} weekly aggregate entries")
        upload_to_r2(weekly_csv_path, R2_UPLOAD_WEEK_NAME)


def calculate_monthly_aggregates(local_path: Path):
    """Calculate calendar month-based aggregates from daily data."""
    daily_csv_path = local_path / R2_UPLOAD_DAILY_NAME
    monthly_csv_path = local_path / R2_UPLOAD_MONTH_NAME
    daily_data = load_existing_csv(daily_csv_path)
    
    if not daily_data:
        print("⚠️ No daily data found for monthly aggregation")
        return
    
    # Group by stable row key and calendar month
    monthly_aggregates = {}
    for row in daily_data:
        char_name = row["character_name"]
        date_obj = datetime.strptime(row["date"], "%Y-%m-%d")
        month_key = date_obj.strftime("%Y-%m")
        key = (char_name, month_key)
        
        if key not in monthly_aggregates:
            monthly_aggregates[key] = {
                "character_name": char_name,
                "month": month_key,
                "level_start": int(row["level"]),
                "level_end": int(row["level"]),
                "first_level": int(row["level"]),
                "last_level": int(row["level"]),
                "first_level_exp": int(row.get("current_level_exp", 0)),
                "last_level_exp": int(row.get("current_level_exp", 0)),
                "dates": [row["date"]]
            }
        else:
            monthly_aggregates[key]["last_level"] = int(row["level"])
            monthly_aggregates[key]["last_level_exp"] = int(row.get("current_level_exp", 0))
            monthly_aggregates[key]["level_end"] = int(row["level"])
            monthly_aggregates[key]["dates"].append(row["date"])
    
    # Convert to list and calculate exp gain with level accounting
    monthly_rows = []
    for agg in monthly_aggregates.values():
        total_exp = 0
        
        # If same level, simple subtraction
        if agg["first_level"] == agg["last_level"]:
            total_exp = agg["last_level_exp"] - agg["first_level_exp"]
        else:
            # Level changed: add remaining exp from first level + all intermediate levels + current progress
            first_level = agg["first_level"]
            last_level = agg["last_level"]
            
            # EXP needed to complete first level
            if first_level < 300 and EXP_TABLE.get(first_level):
                total_exp += EXP_TABLE[first_level] - agg["first_level_exp"]
            
            # EXP from all completed intermediate levels
            for lvl in range(first_level + 1, last_level):
                if lvl < 300 and EXP_TABLE.get(lvl):
                    total_exp += EXP_TABLE[lvl]
            
            # Current progress on last level
            total_exp += agg["last_level_exp"]
        
        monthly_rows.append({
            "character_name": agg["character_name"],
            "month": agg["month"],
            "total_exp_gain": total_exp,
            "level_start": agg["first_level"],
            "level_end": agg["last_level"],
            "days_tracked": len(agg["dates"])
        })
    
    # Sort by month (newest first) then name column
    monthly_rows.sort(key=lambda x: (x["month"], x["character_name"]), reverse=True)
    
    # Keep only last 3 months of data
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)
    cutoff_month = cutoff_date.strftime("%Y-%m")
    monthly_rows = [row for row in monthly_rows if row["month"] >= cutoff_month]
    
    if monthly_rows:
        fieldnames = ["character_name", "month", "total_exp_gain", "level_start", "level_end", "days_tracked"]
        with open(monthly_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(monthly_rows)
        print(f"✓ Saved {len(monthly_rows)} monthly aggregate entries")
        upload_to_r2(monthly_csv_path, R2_UPLOAD_MONTH_NAME)



def should_add_new_entry(csv_path: Path, char_name: str, today_str: str, new_timestamp: str) -> bool:
    """
    Check if we should add this entry.
    Keep FIRST (earliest) entry per stable row key per calendar day.
    Discard newer attempts on the same day.
    """
    if not csv_path.exists():
        return True  # Brand new file, add it
    
    existing_data = load_existing_csv(csv_path)
    today_date = datetime.strptime(today_str, "%Y-%m-%d").date()
    
    # Find any existing entry for this row key on this date
    for row in existing_data:
        if row.get("character_name") != char_name:
            continue
        
        row_date_str = row.get("date", "")
        try:
            row_date = datetime.strptime(row_date_str, "%Y-%m-%d").date()
            if row_date == today_date:
                # Entry exists for today - check timestamps
                existing_ts = row.get("timestamp", "")
                if existing_ts < new_timestamp:
                    # Existing entry is OLDER - keep it, discard new one
                    logging.info("Skipping new row: an earlier timestamp already exists for this row key today.")
                    return False
                else:
                    # New entry is older (shouldn't happen) - allow replacement
                    return True
        except ValueError:
            continue
    
    return True  # No entry for today yet, add this one

def upload_to_r2(local_file: Path, r2_key: str):
    """Upload file to R2 bucket."""
    try:
        s3_client.upload_file(
            str(local_file),
            R2_BUCKET,
            r2_key
        )
        print("✓ Upload to R2 completed.")
    except Exception as e:
        print("✗ Error uploading to R2 (object key omitted from logs).")

def deduplicate_daily_data(local_path: Path):
    """Remove exact duplicates from daily data file."""
    csv_path = local_path / R2_UPLOAD_DAILY_NAME
    
    if not csv_path.exists():
        return
    
    existing_data = load_existing_csv(csv_path)
    
    if not existing_data:
        return
    
    # Unique key: name column + date + level + exp snapshot
    seen = set()
    deduplicated_data = []
    duplicates_removed = 0
    
    for row in existing_data:
        # Create a unique key for this entry
        key = (
            row.get("character_name", ""),
            row.get("date", ""),
            row.get("level", ""),
            row.get("current_level_exp", "")
        )
        
        if key not in seen:
            seen.add(key)
            deduplicated_data.append(row)
        else:
            duplicates_removed += 1
    
    if duplicates_removed > 0:
        print(f"⚠ Found and removed {duplicates_removed} duplicate entries")
        
        # Save deduplicated data
        fieldnames = [
        "character_name", "date", "timestamp", "level", "current_level_exp", "daily_exp_gain",
        "overall_rank", "achievement_rank", "achievement_score", "fame_rank",
        "fame_points", "job_rank", "legion_rank", "world_rank", "job_name",
        "world_id", "character_image_url", "weekly_exp_gain",
        "weekly_overall_rank", "weekly_fame_rank",
        "monthly_overall_rank", "monthly_fame_rank",
        "legendary_overall_rank", "legendary_fame_rank",
    ]

        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(deduplicated_data)
        
        print(f"✓ Deduplicated data saved")
    else:
        print(f"✓ No duplicates found")


def calculate_daily_exp_gain(char_name: str, today_date: str, today_level: int, today_exp: int, existing_data: List[Dict]) -> int:
    """Calculate daily EXP gain with level change handling."""
    
    # Find previous calendar-day entry for this row key
    previous_entry = None
    for row in reversed(existing_data):
        if row["character_name"] != char_name:
            continue
        
        if row["date"] == today_date:
            continue  # Skip today's entry itself
        
        previous_entry = row
        break
    
    if not previous_entry:
        return 0  # No previous data, can't calculate gain
    
    prev_level = int(previous_entry["level"])
    prev_exp = int(previous_entry["current_level_exp"])
    
    # Same level: simple subtraction
    if today_level == prev_level:
        return max(0, today_exp - prev_exp)  # Prevent negative gains
    
    # Level up case: use EXP table calculation
    total_exp_gain = 0
    
    # EXP needed to complete previous level
    if prev_level < 300 and EXP_TABLE.get(prev_level):
        total_exp_gain += EXP_TABLE[prev_level] - prev_exp
    
    # EXP from all completed intermediate levels
    for lvl in range(prev_level + 1, today_level):
        if lvl < 300 and EXP_TABLE.get(lvl):
            total_exp_gain += EXP_TABLE[lvl]
    
    # Current progress on today's level
    total_exp_gain += today_exp
    
    return total_exp_gain


def finalize_daily_data(all_character_data: List[Dict], local_path: Path):
    """Save all daily data at once and upload to R2."""
    csv_path = local_path / R2_UPLOAD_DAILY_NAME

    # Load existing data
    existing_data = load_existing_csv(csv_path)

    # Remove old entries (>60 days)
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%d")
    existing_data = [row for row in existing_data if row["date"] >= cutoff_date]

    # Get current UTC timestamp once
    utc_now = datetime.now(timezone.utc)
    new_timestamp = utc_now.isoformat()

    for new_data in all_character_data:
        char_name = new_data["character_name"]
        today_str = new_data["date"]
    
        # Use new check: only add if no earlier entry exists for today
        if not should_add_new_entry(csv_path, char_name, today_str, new_timestamp):
            print("⏭️ Skipping one row — keeping earlier entry from today")
            continue
    
        # Remove any existing entry for this row key + date
        existing_data = [row for row in existing_data
                        if not (row["character_name"] == char_name and row["date"] == today_str)]

        print("✓ Adding new daily entry for one row key")
        new_data["timestamp"] = new_timestamp
        
        # Calculate daily_exp_gain AFTER removing old entry
        new_data["daily_exp_gain"] = calculate_daily_exp_gain(
            char_name,
            today_str,
            int(new_data["level"]),
            int(new_data["current_level_exp"]),
            existing_data,
        )

        existing_data.append(new_data)

    # Sort by date then name column
    existing_data.sort(key=lambda x: (x["date"], x["character_name"]))

    fieldnames = [
        "character_name", "date", "timestamp", "level", "current_level_exp", "daily_exp_gain",
        "overall_rank", "achievement_rank", "achievement_score", "fame_rank",
        "fame_points", "job_rank", "legion_rank", "world_rank", "job_name",
        "world_id", "character_image_url", "weekly_exp_gain",
        "weekly_overall_rank", "weekly_fame_rank",
        "monthly_overall_rank", "monthly_fame_rank",
        "legendary_overall_rank", "legendary_fame_rank",
    ]


    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(existing_data)

    print("✓ Saved daily CSV locally.")
    upload_to_r2(csv_path, R2_UPLOAD_DAILY_NAME)





def main() -> int:
    """Run one batch: R2 sync, ranking pulls, CSV merge, aggregates. Returns success count."""
    print(f"Starting MapleStory data collection - {datetime.now(timezone.utc)}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("Pulling existing CSVs from R2 …")
    r2_download_daily_or_exit(DATA_DIR)
    r2_download_optional_week_month(DATA_DIR)

    print("\nChecking for duplicates in existing data...")
    deduplicate_daily_data(DATA_DIR)

    total = len(MY_CHARACTERS)
    print(f"\nFetching data for {total} indexed subjects in this batch …")
    all_character_data = []
    for i, subject_name in enumerate(MY_CHARACTERS, 1):
        print(f"  [{i}/{total}] Fetching ranking row …")
        char_data = fetch_ranking_row(subject_name, MAPLE_REBOOT_INDEX)
        if char_data:
            all_character_data.append(char_data)
            print("    ✓ Success")
        else:
            print("    ✗ Failed")

        if i < total:
            time.sleep(2)

    print(f"\n✓ Fetched {len(all_character_data)} of {total} indexed subjects in this batch")

    print("\nSaving all daily data...")
    finalize_daily_data(all_character_data, DATA_DIR)

    print("\nCalculating weekly aggregates...")
    calculate_weekly_aggregates(DATA_DIR)

    print("\nCalculating monthly aggregates...")
    calculate_monthly_aggregates(DATA_DIR)

    print("\n✓ Collection complete!")
    return len(all_character_data)


if __name__ == "__main__":
    configure_runtime()
    try:
        fetched = main()
        timestamp = int(time.time())
        total = len(MY_CHARACTERS)
        job = f" (job {MAPLE_JOB_LABEL})" if MAPLE_JOB_LABEL else ""
        send_discord_alert(
            f"✅ MapleStory data{job} — fetched {fetched}/{total} indexed subjects at <t:{timestamp}:f>"
        )
    except SystemExit:
        raise
    except Exception as e:
        timestamp = int(time.time())
        user_id = (os.getenv("DISCORD_USER_ID") or "").strip()
        mention = f"<@{user_id}> " if user_id else ""
        send_discord_alert(format_failure_for_discord(mention, timestamp, e))
        print(
            "MapleStory data collection failed (see Discord for details if configured).",
            file=sys.stderr,
        )
        raise