"""Weekly aggregation of public_stats and push to DHIS2 via the dataValueSets API.

Usage:
    python -m app.dhis2                    # current ISO week
    python -m app.dhis2 --week 2026-W45
    python -m app.dhis2 --week 2026-W45 --dry-run

The demo data set "SuNoogo perinatal screening" (4 data elements) is created or updated on
every run, since public demo instances are reset regularly. Only weekly totals are sent.
"""

import argparse
import logging
import os
import re
import sys
from datetime import date

import httpx
from dotenv import load_dotenv

log = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://play.dhis2.org/demo"  # redirects to the current stable demo
DEFAULT_ORG_UNIT = "ImspTQPwCqd"  # root org unit of the DHIS2 demo database
DEFAULT_CATEGORY_COMBO = "bjDvmb4bfuf"  # "default" category combo

DATA_SET_ID = "SuNoogoDS01"
# public_stats column -> fixed DHIS2 data element uid (11 chars, so reruns update in place)
DATA_ELEMENTS = {
    "sessions_completed": ("SuNoDEcmp01", "Sessions completed"),
    "level_green": ("SuNoDEgrn01", "Level green"),
    "level_orange": ("SuNoDEorg01", "Level orange"),
    "level_red": ("SuNoDEred01", "Level red"),
}

WEEK_RE = re.compile(r"(\d{4})-W(\d{2})")


def parse_week(week: str) -> str:
    """'2026-W45' -> DHIS2 weekly period '2026W45'."""
    match = WEEK_RE.fullmatch(week)
    if not match or not 1 <= int(match.group(2)) <= 53:
        raise ValueError(f"invalid ISO week {week!r}, expected e.g. 2026-W45")
    return f"{match.group(1)}W{int(match.group(2))}"


def current_week(today: date) -> str:
    year, week, _ = today.isocalendar()
    return f"{year}-W{week:02d}"


def week_values(stats_rows: list[dict], week: str) -> dict[str, int]:
    """Values of the 4 indicators for one ISO week; zeros if nothing happened that week."""
    row = next((r for r in stats_rows if r.get("iso_week") == week), {})
    return {field: int(row.get(field) or 0) for field in DATA_ELEMENTS}


def metadata_payload(org_unit: str, category_combo: str = DEFAULT_CATEGORY_COMBO) -> dict:
    combo = {"id": category_combo}
    # Data elements only take metadata sharing; data read/write is set on the data set.
    metadata_sharing = {"public": "rw------"}
    data_elements = [
        {
            "id": uid,
            "name": f"SuNoogo - {label}",
            "shortName": f"SuNoogo {label}",
            "valueType": "INTEGER_ZERO_OR_POSITIVE",
            "domainType": "AGGREGATE",
            "aggregationType": "SUM",
            "zeroIsSignificant": True,  # a week with zero cases is a real report
            "categoryCombo": combo,
            "sharing": metadata_sharing,
        }
        for uid, label in DATA_ELEMENTS.values()
    ]
    data_set = {
        "id": DATA_SET_ID,
        "name": "SuNoogo perinatal screening",
        "shortName": "SuNoogo screening",
        "periodType": "Weekly",
        "categoryCombo": combo,
        "openFuturePeriods": 1,
        "dataSetElements": [
            {"dataSet": {"id": DATA_SET_ID}, "dataElement": {"id": uid}}
            for uid, _ in DATA_ELEMENTS.values()
        ],
        "organisationUnits": [{"id": org_unit}],
        "sharing": {"public": "rwrw----"},
    }
    return {"dataElements": data_elements, "dataSets": [data_set]}


def data_value_set(week: str, values: dict[str, int], org_unit: str) -> dict:
    return {
        "dataSet": DATA_SET_ID,
        "period": parse_week(week),
        "orgUnit": org_unit,
        "dataValues": [
            {"dataElement": DATA_ELEMENTS[field][0], "value": str(value)}
            for field, value in values.items()
        ],
    }


def resolve_base_url(client: httpx.Client, url: str) -> str:
    """Resolve redirects (e.g. play.dhis2.org/demo) up front, with GET: POSTs must not go
    through a 302, and httpx drops credentials on cross-host redirects."""
    target = url.rstrip("/") + "/api/system/info"
    for _ in range(5):
        response = client.get(target)
        if response.is_redirect and "/login" not in response.headers.get("location", ""):
            target = str(response.next_request.url)
            continue
        response.raise_for_status()  # also raises on a redirect to /login (bad credentials)
        return target.removesuffix("/api/system/info")
    raise RuntimeError(f"too many redirects from {url}")


def ensure_metadata(client: httpx.Client, base: str, org_unit: str) -> None:
    response = client.post(
        f"{base}/api/metadata",
        params={"importStrategy": "CREATE_AND_UPDATE", "atomicMode": "ALL"},
        json=metadata_payload(org_unit),
    )
    body = response.json()
    if response.status_code >= 400 or body.get("status") == "ERROR":
        raise RuntimeError(f"DHIS2 metadata import failed: {response.status_code} {body}")


def push(client: httpx.Client, base: str, payload: dict, dry_run: bool) -> dict:
    response = client.post(
        f"{base}/api/dataValueSets",
        params={"importStrategy": "CREATE_AND_UPDATE", "dryRun": str(dry_run).lower()},
        json=payload,
    )
    body = response.json()
    summary = body.get("response", body)  # newer versions wrap the import summary
    if response.status_code >= 400 or summary.get("status") == "ERROR":
        raise RuntimeError(f"DHIS2 data import failed: {response.status_code} {body}")
    return summary.get("importCount", {})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Push weekly SuNoogo totals to DHIS2.")
    parser.add_argument("--week", default=current_week(date.today()), help="ISO week, e.g. 2026-W45")
    parser.add_argument("--dry-run", action="store_true", help="validate without saving in DHIS2")
    args = parser.parse_args(argv)
    parse_week(args.week)

    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    from app import db  # imported late so the pure helpers above need no Supabase settings

    values = week_values(db.fetch_public_stats(), args.week)
    org_unit = os.environ.get("DHIS2_ORG_UNIT") or DEFAULT_ORG_UNIT
    auth = (os.environ["DHIS2_USERNAME"], os.environ["DHIS2_PASSWORD"])

    with httpx.Client(auth=auth, timeout=60) as client:
        base = resolve_base_url(client, os.environ.get("DHIS2_BASE_URL") or DEFAULT_BASE_URL)
        ensure_metadata(client, base, org_unit)
        counts = push(client, base, data_value_set(args.week, values, org_unit), args.dry_run)

    mode = "dry run" if args.dry_run else "pushed"
    print(f"{mode} {args.week} to {base}: values={values} importCount={counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
