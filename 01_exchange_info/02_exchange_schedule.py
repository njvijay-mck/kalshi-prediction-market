"""01_exchange_info/02_exchange_schedule.py

Demonstrates: client.get_exchange_schedule()
- Trading hours and maintenance windows.
- Public endpoint: no credentials needed.

SDK response type: GetExchangeScheduleResponse
  .schedule -> Schedule
    .standard_hours -> list of StandardHours objects, each with per-day DailySchedule lists
    .maintenance_windows -> list of MaintenanceWindow objects

Run:
    uv run python 01_exchange_info/02_exchange_schedule.py
"""

from auth.client import get_client

client = get_client()

print("=== Exchange Schedule ===\n")
resp = client.get_exchange_schedule()
schedule = resp.schedule

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

print("Standard trading hours:")
hours_list = schedule.standard_hours or []
# standard_hours may be a single object or a list
if not isinstance(hours_list, list):
    hours_list = [hours_list]

if not hours_list:
    print("  (none)")
else:
    for hours in hours_list:
        start = getattr(hours, "start_time", None)
        end = getattr(hours, "end_time", None)
        if start or end:
            print(f"  Valid: {start} → {end}")
        for day in DAYS:
            windows = getattr(hours, day, None) or []
            if windows:
                slots = []
                for w in windows:
                    open_t = getattr(w, "open_time", "?")
                    close_t = getattr(w, "close_time", "?")
                    slots.append(f"{open_t}–{close_t}")
                print(f"  {day.capitalize():<12}: {', '.join(slots)}")

print("\nMaintenance windows:")
if schedule.maintenance_windows:
    for window in schedule.maintenance_windows:
        start = getattr(window, "start_datetime", getattr(window, "start_time", "?"))
        end = getattr(window, "end_datetime", getattr(window, "end_time", "?"))
        print(f"  {start} → {end}")
else:
    print("  (none)")
