"""List the follow-up questionnaires that are due (orange results, 14 days later).

Usage:
    python -m app.followups
"""

import sys
from datetime import date

from dotenv import load_dotenv


def format_followups(rows: list[dict], today: date) -> str:
    if not rows:
        return f"No follow-up due on {today.isoformat()}."
    lines = [f"{len(rows)} follow-up(s) due on {today.isoformat()}:"]
    for row in rows:
        lines.append(f"  {row['woman_code']}  due {row['followup_due']}  CHW {row['chw_phone']}")
    return "\n".join(lines)


def main() -> int:
    load_dotenv()
    from app import db

    today = date.today()
    print(format_followups(db.fetch_due_followups(today), today))
    return 0


if __name__ == "__main__":
    sys.exit(main())
