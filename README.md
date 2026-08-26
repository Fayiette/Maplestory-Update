# MapleStory automation (GitHub Actions)

`[maplechardata.py](maplechardata.py)` pulls NA MapleStory ranking data from Nexon’s public API, merges into daily/weekly/monthly CSVs, and syncs with Cloudflare R2.

[![group 1](https://github.com/Fayiette/Maplestory-Update/actions/workflows/maplechardata-fetch-01.yml/badge.svg)](https://github.com/Fayiette/Maplestory-Update/actions/workflows/maplechardata-fetch-01.yml)
[![group 2](https://github.com/Fayiette/Maplestory-Update/actions/workflows/maplechardata-fetch-02.yml/badge.svg)](https://github.com/Fayiette/Maplestory-Update/actions/workflows/maplechardata-fetch-02.yml)
[![group 3](https://github.com/Fayiette/Maplestory-Update/actions/workflows/maplechardata-fetch-03.yml/badge.svg)](https://github.com/Fayiette/Maplestory-Update/actions/workflows/maplechardata-fetch-03.yml)
[![group 3](https://github.com/Fayiette/Maplestory-Update/actions/workflows/maplechardata-fetch-04.yml/badge.svg)](https://github.com/Fayiette/Maplestory-Update/actions/workflows/maplechardata-fetch-04.yml)
[![group 3](https://github.com/Fayiette/Maplestory-Update/actions/workflows/maplechardata-fetch-05.yml/badge.svg)](https://github.com/Fayiette/Maplestory-Update/actions/workflows/maplechardata-fetch-05.yml)

## Behaviour

1. **R2 download** — The daily CSV object (`R2_UPLOAD_DAILY_NAME`) **must** exist in the bucket. If the download fails (missing object or network/auth error), the process exits with code 1. Weekly and monthly objects are optional; if missing, aggregates are rebuilt from daily data when possible.
2. **Fetch** — Values listed in `MY_CHARACTERS` are queried with a short delay between each request to reduce timeouts.
3. **Upload** — Daily row merge, dedupe, weekly/monthly aggregates, then upload CSVs back to R2.

## Logs (public CI vs private Discord)

- **GitHub Actions logs** — Progress uses counts and generic phrases only (no values from `MY_CHARACTERS`, no webhook URLs, no R2 credentials).
- **Discord** — Optional failure detail with capped length. **GitHub logs never include** Discord user IDs, webhooks, subject strings from env, or R2 details. **Discord failure posts** scrub tracebacks/exceptions (query parameters that mirror env subjects, R2 credentials and endpoints, configured object key strings, values from `MY_CHARACTERS`, raw webhook URL) while still allowing an `<@user_id>` **mention prefix** when `DISCORD_USER_ID` is set so you get notified in your private channel.

## Environment variables


| Variable                                                               | Required | Notes                                                                                                                                                                                         |
| ---------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `R2_BUCKET`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_ENDPOINT` | Yes      | R2 S3-compatible API                                                                                                                                                                          |
| `R2_UPLOAD_DAILY_NAME`, `R2_UPLOAD_WEEK_NAME`, `R2_UPLOAD_MONTH_NAME`  | Yes      | Non-empty object keys for the three CSVs (no defaults in the script; set in env / secrets).                                                                                                   |
| `MAPLE_RANKING_API_URL`                                                | Yes      | Ranking HTTP base URL (no default in the script; set from publisher docs).                                                                                                                    |
| `MAPLE_REBOOT_INDEX`                                                   | No       | Default `0`                                                                                                                                                                                   |
| `MY_CHARACTERS`                                                        | Yes      | Semicolon or comma separated values for **this** run only                                                                                                                                     |
| `MY_CHARACTERS_GROUP_1` … `_5`                                         | —        | **Not read by the script** — use in GitHub Environment secrets (see workflows). Optional parallel keys in [.env](.env) for local copy/paste; set `MY_CHARACTERS` to one line to test a batch. |
| `MAPLE_JOB_LABEL`                                                      | No       | Shown in Discord only (e.g. `1`…`5` for workflow group)                                                                                                                                       |
| `DISCORD_WEBHOOK_URL`                                                  | No       | Also accepts legacy `DISCORD_WEBHOOK`                                                                                                                                                         |
| `DISCORD_USER_ID`                                                      | No       | Mention on failure (Discord only)                                                                                                                                                             |


Bootstrap: upload a valid daily CSV (with the header row this script writes) to R2 at the object key you set in `R2_UPLOAD_DAILY_NAME` before the first automated run.

## GitHub Actions (five workflows)

Workflows live under `[.github/workflows/](.github/workflows/)` inside this folder. There are **five** files so you can split your subject list across environment secrets `MY_CHARACTERS_GROUP_1` … `MY_CHARACTERS_GROUP_5` (for example nine subjects per group on the first four jobs and the remainder on the fifth).

- `**environment: prod`** — All secrets should be defined under **Settings → Environments → prod → Environment secrets** so only prod-scoped values are used.
- **Concurrency** — Every workflow declares `concurrency.group: maplechardata-r2` with `cancel-in-progress: false`, so if another Maple workflow is running, the new run **waits** instead of overlapping R2 merges.
- **Cron** — Each file runs **once per day**, **one hour apart** (07:00–11:00 UTC by default: `0 7`, `0 8`, `0 9`, `0 10`, `0 11`). Adjust to your timezone and preference. Concurrency still queues overlapping runs on the shared R2 lock.

Install in CI from repo root:

```bash
pip install -r Maplestory/requirements.txt
python Maplestory/maplechardata.py
```

## Local run

```bash
cd Maplestory
pip install -r requirements.txt
cp .env.example .env   # if you do not already have .env
# Edit .env: add R2_* and DISCORD_WEBHOOK_URL (see table above). .env is gitignored.
python maplechardata.py
```

## License

See [LICENSE](LICENSE) (GNU AGPL-3.0).
