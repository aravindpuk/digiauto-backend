from datetime import datetime, time, timedelta
from django.utils import timezone


def resolve_date_range(request):
    """
    Returns (start_dt, end_dt, period, start_date, end_date) — timezone-aware
    datetimes spanning the full days requested.

    Query params:
        period: "today" (default) | "week" | "month" | "custom"
        start_date / end_date: "YYYY-MM-DD", used when period=custom
    """
    period = (request.query_params.get("period") or "today").lower()
    today = timezone.localdate()

    if period == "custom":
        start_date = _parse_date(request.query_params.get("start_date")) or today
        end_date = _parse_date(request.query_params.get("end_date")) or today
        if end_date < start_date:
            start_date, end_date = end_date, start_date
    elif period == "week":
        start_date = today - timedelta(days=6)
        end_date = today
    elif period == "month":
        start_date = today.replace(day=1)
        end_date = today
    else:
        period = "today"
        start_date = today
        end_date = today

    start_dt = timezone.make_aware(datetime.combine(start_date, time.min))
    end_dt = timezone.make_aware(datetime.combine(end_date, time.max))
    return start_dt, end_dt, period, start_date, end_date


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None