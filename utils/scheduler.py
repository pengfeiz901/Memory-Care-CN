# memorycare_app/utils/scheduler.py
from __future__ import annotations
from datetime import datetime, time
from typing import List, Optional

def _parse_specific_times(csv_times: Optional[str]) -> List[time]:
    if not csv_times:
        return []
    out = []
    for t in csv_times.split(","):
        t = t.strip()
        try:
            hh, mm = t.split(":")
            out.append(time(int(hh), int(mm)))
        except:
            pass
    return out

def next_due_window(now: datetime, times_per_day: int, specific_times: Optional[str]) -> Optional[str]:
    """Return a friendly message if a dose is due now/soon (+/- 5 min)."""
    if times_per_day <= 0:
        return None
    window = 5  # minutes

    if specific_times:
        for tt in _parse_specific_times(specific_times):
            dose_dt = now.replace(hour=tt.hour, minute=tt.minute, second=0, microsecond=0)
            delta = abs((dose_dt - now).total_seconds()) / 60
            if delta <= window:
                return f"Medication time window right now (~{tt.strftime('%H:%M')})."
    else:
        # equal spacing across day
        minutes_per = int(24 * 60 / times_per_day)
        slots = [minutes_per * i for i in range(times_per_day)]
        now_min = now.hour * 60 + now.minute
        for sm in slots:
            delta = abs(sm - now_min)
            if delta <= window:
                hh, mm = divmod(sm, 60)
                return f"Medication time window right now (~{hh:02d}:{mm:02d})."
    return None
