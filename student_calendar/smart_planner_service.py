# student_calendar/smart_planner_service.py
# Khan - Smart Planner Algorithm Service
#
# This file contains the entire smart planner algorithm.
# It is called by the /smart-plan/generate/ endpoint (Task 8).
# It reads from the database but does NOT write to it - Task 8 is preview-only.
#
# How it works:
#   Phase 1 - Score and rank templates by priority (so tightest/hardest go first)
#   Phase 2 - Greedy placement (place each instance in the best available slot)
#   Phase 3 - Improvement pass (swap pairs of events if it improves the plan)

import math
from datetime import date, timedelta, datetime
from collections import defaultdict


# =============================================================
# CONSTANTS
# =============================================================

# Khan - Every time slot in the grid is 15 minutes wide
# So a 1 hour event takes 4 slots, a 2 hour event takes 8 slots, etc.
SLOT_MINUTES = 15


# =============================================================
# SECTION 1 - HELPER UTILITIES
# Small reusable functions used throughout the algorithm
# =============================================================

def time_to_slot_index(time_minutes, day_start_minutes):
    # Khan - Turn a time (minutes from midnight) into a grid array index
    # Example: day starts at 480 (08:00), so 09:00 (540) = slot index 4
    return (time_minutes - day_start_minutes) // SLOT_MINUTES


def slot_index_to_time(slot_index, day_start_minutes):
    # Khan - Reverse of above: turn a grid slot index back into minutes from midnight
    return day_start_minutes + slot_index * SLOT_MINUTES


def minutes_to_time_str(minutes):
    # Khan - Turn a raw minute count into a readable "HH:MM" string
    # e.g. 630 -> "10:30",  480 -> "08:00"
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def time_str_to_minutes(time_str):
    # Khan - Turn a "HH:MM" string into minutes from midnight
    # e.g. "09:00" -> 540,  "10:30" -> 630
    parts = time_str.split(':')
    return int(parts[0]) * 60 + int(parts[1])


def get_day_bitmask(day_date):
    # Khan - Get the bitmask value for the day of the week of a given date
    # We use the same system as the Event model:
    # Mon=1, Tue=2, Wed=4, Thu=8, Fri=16, Sat=32, Sun=64
    # Python's weekday() gives: 0=Mon, 1=Tue, ..., 5=Sat, 6=Sun
    weekday = day_date.weekday()
    if weekday == 6:
        return 64   # Sunday: Python gives 6 but our bitmask uses 64
    return 1 << weekday  # Mon: 1<<0=1, Tue: 1<<1=2, Wed: 1<<2=4, etc.


# =============================================================
# SECTION 2 - TIME GRID
# The time grid is how the algorithm knows which slots are free.
# It is a dict of lists:
#   key   = date string "YYYY-MM-DD"
#   value = list of booleans, one per 15-min slot in the daily window
#             True  = slot is free (event can go here)
#             False = slot is occupied (blocked by an existing event + buffer)
# =============================================================

def _block_event_in_grid(grid, se, day_start_mins, day_end_mins, buffer_minutes):
    # Khan - block out the slots for one existing event in the grid
    if se.placed_start is None or se.placed_end is None:
        return

    event_date_str = se.placed_start.date().isoformat()
    if event_date_str not in grid:
        return

    total_slots = len(grid[event_date_str])
    start_mins = se.placed_start.hour * 60 + se.placed_start.minute
    end_mins   = se.placed_end.hour   * 60 + se.placed_end.minute

    padded_start = max(day_start_mins, start_mins - buffer_minutes)
    padded_end   = min(day_end_mins,   end_mins   + buffer_minutes)

    s = time_to_slot_index(padded_start, day_start_mins)
    e = time_to_slot_index(padded_end,   day_start_mins)

    for i in range(max(0, s), min(total_slots, e)):
        grid[event_date_str][i] = False


def build_time_grid(date_range, existing_scheduled_events, day_start_str, day_end_str, buffer_minutes):
    # Khan - Build the starting time grid for the whole planning range.
    # All slots start as free (True), then we mark occupied ones (False).
    day_start_mins = time_str_to_minutes(day_start_str)
    day_end_mins   = time_str_to_minutes(day_end_str)
    total_slots    = (day_end_mins - day_start_mins) // SLOT_MINUTES

    grid = {}
    for d in date_range:
        grid[d.isoformat()] = [True] * total_slots

    for se in existing_scheduled_events:
        _block_event_in_grid(grid, se, day_start_mins, day_end_mins, buffer_minutes)

    return grid


def mark_event_in_grid(grid, date_str, start_mins, duration_mins, buffer_mins, day_start_mins, day_end_mins):
    # Khan - Mark an event (plus its buffer) as occupied in the grid.
    total_slots  = len(grid.get(date_str, []))
    end_mins     = start_mins + duration_mins

    padded_start = max(day_start_mins, start_mins - buffer_mins)
    padded_end   = min(day_end_mins,   end_mins   + buffer_mins)

    s = time_to_slot_index(padded_start, day_start_mins)
    e = time_to_slot_index(padded_end,   day_start_mins)

    for i in range(max(0, s), min(total_slots, e)):
        grid[date_str][i] = False


def unmark_event_in_grid(grid, date_str, start_mins, duration_mins, buffer_mins, day_start_mins, day_end_mins):
    # Khan - Undo an event's footprint in the grid (set slots back to free).
    total_slots  = len(grid.get(date_str, []))
    end_mins     = start_mins + duration_mins

    padded_start = max(day_start_mins, start_mins - buffer_mins)
    padded_end   = min(day_end_mins,   end_mins   + buffer_mins)

    s = time_to_slot_index(padded_start, day_start_mins)
    e = time_to_slot_index(padded_end,   day_start_mins)

    for i in range(max(0, s), min(total_slots, e)):
        grid[date_str][i] = True


# =============================================================
# SECTION 3 - PHASE 1: TEMPLATE SCORING
# Before placing anything, we rank flexible templates by priority.
# Tightest/most-constrained events go first so they get the best slots.
# =============================================================

def _calc_importance_score(importance):
    # Khan - flip importance so Critical=1.0, Very Low=0.0
    return 1.0 - ((importance - 1) / 4.0)


def _calc_tightness_score(repeat_days, user_selected_days_bitmask):
    # Khan - how restricted is this event's day selection?
    if repeat_days == 0:
        valid_days_count = bin(user_selected_days_bitmask).count('1')
    else:
        overlap = repeat_days & user_selected_days_bitmask
        valid_days_count = bin(overlap).count('1')
        if valid_days_count == 0:
            valid_days_count = 1
    return 1.0 - (valid_days_count / 7.0)


def _calc_duration_score(duration, all_flexible_templates):
    # Khan - longer events are harder to fit so they score higher
    max_duration = max(
        (t.get('duration_minutes') or 60) for t in all_flexible_templates
    ) if all_flexible_templates else 60
    return duration / max_duration if max_duration > 0 else 0.0


def _calc_scarcity_score(created_count):
    # Khan - fewer instances = more precious
    return 1.0 / math.sqrt(max(1, created_count))


def score_template(template_data, all_flexible_templates, user_selected_days_bitmask):
    # Khan - Calculate a priority score (0.0 to 1.0) for one flexible template.
    # Higher score = place this template's instances earlier.
    importance_score = _calc_importance_score(template_data.get('importance', 3))
    repeat_days = template_data.get('repeat_days') or 0
    tightness_score = _calc_tightness_score(repeat_days, user_selected_days_bitmask)
    duration = template_data.get('duration_minutes') or 60
    duration_score = _calc_duration_score(duration, all_flexible_templates)
    scarcity_score = _calc_scarcity_score(template_data.get('created_count', 1))

    priority = (
        0.35 * tightness_score +
        0.30 * importance_score +
        0.20 * duration_score  +
        0.15 * scarcity_score
    )
    return round(priority, 4)


# =============================================================
# SECTION 4 - PHASE 2: FIND VALID SLOTS + SCORE THEM
# =============================================================

def _day_passes_constraints(d, day_bitmask, selected_days, repeat_days, template_id, date_str, placed_date_set):
    # Khan - check if a day passes all hard constraints for slot finding
    if not (selected_days & day_bitmask):
        return False
    if repeat_days != 0 and not (repeat_days & day_bitmask):
        return False
    if (template_id, date_str) in placed_date_set:
        return False
    return True


def _scan_day_for_slots(day_slots, total_slots, slots_needed, day_start_mins, day_end_mins, duration_mins, date_str):
    # Khan - scan one day's slots and return all valid start positions
    results = []
    for slot_index in range(total_slots - slots_needed + 1):
        if all(day_slots[slot_index + k] for k in range(slots_needed)):
            start_mins = slot_index_to_time(slot_index, day_start_mins)
            end_mins = start_mins + duration_mins
            if end_mins <= day_end_mins:
                results.append((date_str, start_mins))
    return results


def find_valid_slots(template_data, time_grid, constraints, placed_date_set):
    # Khan - Find all valid (date_str, start_mins) positions for one instance.
    day_start_mins = time_str_to_minutes(constraints['day_start'])
    day_end_mins   = time_str_to_minutes(constraints['day_end'])
    total_slots    = (day_end_mins - day_start_mins) // SLOT_MINUTES
    duration_mins  = template_data.get('duration_minutes') or 60
    slots_needed   = math.ceil(duration_mins / SLOT_MINUTES)
    repeat_days    = template_data.get('repeat_days') or 0
    template_id    = template_data['id']
    selected_days  = constraints['selected_days_bitmask']

    valid_slots = []
    for date_str in sorted(time_grid.keys()):
        d = date.fromisoformat(date_str)
        day_bitmask = get_day_bitmask(d)

        if not _day_passes_constraints(d, day_bitmask, selected_days, repeat_days, template_id, date_str, placed_date_set):
            continue

        day_results = _scan_day_for_slots(time_grid[date_str], total_slots, slots_needed, day_start_mins, day_end_mins, duration_mins, date_str)
        valid_slots.extend(day_results)

    return valid_slots


def _calc_gap_efficiency(day_slots, start_slot_idx, slots_needed, total_slots, duration_mins, buffer_mins):
    # Khan - how well does the event fill the gap it sits in?
    gap_start = start_slot_idx
    while gap_start > 0 and day_slots[gap_start - 1]:
        gap_start -= 1

    gap_end = start_slot_idx + slots_needed
    while gap_end < total_slots and day_slots[gap_end]:
        gap_end += 1

    gap_size = gap_end - gap_start
    event_with_buffer = math.ceil((duration_mins + buffer_mins) / SLOT_MINUTES)
    return min(1.0, event_with_buffer / gap_size) if gap_size > 0 else 1.0


def _calc_compactness(day_slots, start_slot_idx, total_slots):
    # Khan - how close is this slot to other events on the same day?
    nearest_distance = total_slots
    for i in range(total_slots):
        if not day_slots[i]:
            dist = abs(i - start_slot_idx)
            if dist < nearest_distance:
                nearest_distance = dist

    if nearest_distance == total_slots:
        return 0.5
    return 1.0 - (nearest_distance / total_slots)


def _calc_day_load(day_slots, total_slots):
    # Khan - how much free space is left on this day?
    occupied = sum(1 for s in day_slots if not s)
    return 1.0 - (occupied / total_slots)


def score_slot(date_str, start_mins, time_grid, duration_mins, buffer_mins, day_start_mins, day_end_mins):
    # Khan - Score a candidate slot for an event. Higher = better fit.
    day_slots      = time_grid[date_str]
    total_slots    = len(day_slots)
    slots_needed   = math.ceil(duration_mins / SLOT_MINUTES)
    start_slot_idx = time_to_slot_index(start_mins, day_start_mins)

    gap_efficiency = _calc_gap_efficiency(day_slots, start_slot_idx, slots_needed, total_slots, duration_mins, buffer_mins)
    compactness    = _calc_compactness(day_slots, start_slot_idx, total_slots)
    day_load_score = _calc_day_load(day_slots, total_slots)

    slot_score = (
        0.40 * gap_efficiency +
        0.35 * compactness    +
        0.25 * day_load_score
    )
    return round(slot_score, 4)


# =============================================================
# SECTION 5 - PHASE 2: GREEDY PLACEMENT
# =============================================================

def _place_fixed_instance(instance, template_data, time_grid, duration_mins, buffer_mins, day_start_mins, day_end_mins):
    # Khan - lock in a fixed event and mark its slot
    entry = {
        'schedule_event_id': instance['id'],
        'event_title':       template_data['title'],
        'occurrence_index':  instance['occurrence_index'],
        'placed_start':      instance.get('fixed_start'),
        'placed_end':        instance.get('fixed_end'),
        'template_id':       template_data['id'],
        'is_fixed':          True,
    }
    fixed_start = instance.get('fixed_start')
    if fixed_start:
        try:
            fixed_dt   = datetime.fromisoformat(fixed_start)
            date_str   = fixed_dt.date().isoformat()
            start_mins = fixed_dt.hour * 60 + fixed_dt.minute
            if date_str in time_grid:
                mark_event_in_grid(time_grid, date_str, start_mins, duration_mins, buffer_mins, day_start_mins, day_end_mins)
        except (ValueError, KeyError):
            pass
    return entry


def _build_unplaced_entry(instance, template_data, constraints):
    # Khan - build the dict for an instance that couldnt be placed
    repeat_days = template_data.get('repeat_days') or 0
    selected = constraints['selected_days_bitmask']

    if repeat_days != 0 and not (repeat_days & selected):
        reason = (
            "No valid days — this event requires specific days of the week "
            "that are not included in your selected active days"
        )
    else:
        reason = "No available slot found within the planning range"

    return {
        'schedule_event_id': instance['id'],
        'event_title':       template_data['title'],
        'occurrence_index':  instance['occurrence_index'],
        'reason':            reason,
        'template_id':       template_data['id'],
    }


def _pick_best_slot(valid_slots, time_grid, duration_mins, buffer_mins, day_start_mins, day_end_mins):
    # Khan - score every valid slot and return the best one
    best_score = -1.0
    best_date_str = None
    best_start_mins = None

    for (date_str, start_mins) in valid_slots:
        s = score_slot(date_str, start_mins, time_grid, duration_mins, buffer_mins, day_start_mins, day_end_mins)
        if s > best_score:
            best_score = s
            best_date_str = date_str
            best_start_mins = start_mins

    return best_date_str, best_start_mins, best_score


def _place_flexible_instance(instance, template_data, time_grid, constraints, placed_date_set, day_start_mins, day_end_mins, buffer_mins):
    # Khan - try to find the best slot for a flexible event instance
    duration_mins = template_data.get('duration_minutes') or 60

    valid_slots = find_valid_slots(template_data, time_grid, constraints, placed_date_set)

    if not valid_slots:
        return None, _build_unplaced_entry(instance, template_data, constraints)

    best_date_str, best_start_mins, best_score = _pick_best_slot(valid_slots, time_grid, duration_mins, buffer_mins, day_start_mins, day_end_mins)

    best_end_mins = best_start_mins + duration_mins
    placed_start_str = f"{best_date_str}T{minutes_to_time_str(best_start_mins)}"
    placed_end_str   = f"{best_date_str}T{minutes_to_time_str(best_end_mins)}"

    entry = {
        'schedule_event_id': instance['id'],
        'event_title':       template_data['title'],
        'occurrence_index':  instance['occurrence_index'],
        'placed_start':      placed_start_str,
        'placed_end':        placed_end_str,
        'template_id':       template_data['id'],
        'is_fixed':          False,
        'slot_score':        best_score,
    }

    mark_event_in_grid(time_grid, best_date_str, best_start_mins, duration_mins, buffer_mins, day_start_mins, day_end_mins)
    placed_date_set.add((template_data['id'], best_date_str))

    return entry, None


def run_phase2(ordered_templates, time_grid, constraints):
    # Khan - The main placement loop.
    placed_list   = []
    unplaced_list = []

    day_start_mins = time_str_to_minutes(constraints['day_start'])
    day_end_mins   = time_str_to_minutes(constraints['day_end'])
    buffer_mins    = constraints['buffer_minutes']
    placed_date_set = set()

    for template_data, instances in ordered_templates:
        duration_mins = template_data.get('duration_minutes') or 60
        is_fixed = template_data.get('is_fixed', False)

        for instance in instances:
            if is_fixed:
                entry = _place_fixed_instance(instance, template_data, time_grid, duration_mins, buffer_mins, day_start_mins, day_end_mins)
                placed_list.append(entry)
                continue

            placed, unplaced = _place_flexible_instance(instance, template_data, time_grid, constraints, placed_date_set, day_start_mins, day_end_mins, buffer_mins)
            if placed:
                placed_list.append(placed)
            if unplaced:
                unplaced_list.append(unplaced)

    return placed_list, unplaced_list


# =============================================================
# SECTION 6 - PHASE 3: IMPROVEMENT PASS
# =============================================================

def _parse_placement(p):
    # Khan - extract date, start, end, duration from a placed dict
    p_date  = p['placed_start'].split('T')[0]
    p_start = time_str_to_minutes(p['placed_start'].split('T')[1])
    p_end   = time_str_to_minutes(p['placed_end'].split('T')[1])
    return p_date, p_start, p_end - p_start


def _check_event_fits(time_grid, target_date, target_start, event_duration, day_start_mins, day_end_mins):
    # Khan - check if an event of given duration fits at a target position
    slots_needed = math.ceil(event_duration / SLOT_MINUTES)
    idx = time_to_slot_index(target_start, day_start_mins)
    return (
        target_date in time_grid and
        target_start + event_duration <= day_end_mins and
        idx >= 0 and
        idx + slots_needed <= len(time_grid[target_date]) and
        all(time_grid[target_date][idx + k] for k in range(slots_needed))
    )


def _execute_swap(flexible, i, j, a_date, a_start, a_dur, b_date, b_start, b_dur):
    # Khan - swap the positions of two flexible events
    flexible[i]['placed_start'] = f"{b_date}T{minutes_to_time_str(b_start)}"
    flexible[i]['placed_end']   = f"{b_date}T{minutes_to_time_str(b_start + a_dur)}"
    flexible[j]['placed_start'] = f"{a_date}T{minutes_to_time_str(a_start)}"
    flexible[j]['placed_end']   = f"{a_date}T{minutes_to_time_str(a_start + b_dur)}"


def _try_swap_pair(flexible, i, j, time_grid, buffer_mins, day_start_mins, day_end_mins):
    # Khan - try swapping two flexible events, return True if swap was made
    a, b = flexible[i], flexible[j]
    a_date, a_start, a_dur = _parse_placement(a)
    b_date, b_start, b_dur = _parse_placement(b)

    # Khan - dont swap instances of the same template
    if a['template_id'] == b['template_id']:
        return False

    # Khan - temporarily remove both from grid
    unmark_event_in_grid(time_grid, a_date, a_start, a_dur, buffer_mins, day_start_mins, day_end_mins)
    unmark_event_in_grid(time_grid, b_date, b_start, b_dur, buffer_mins, day_start_mins, day_end_mins)

    a_fits_b = _check_event_fits(time_grid, b_date, b_start, a_dur, day_start_mins, day_end_mins)
    b_fits_a = _check_event_fits(time_grid, a_date, a_start, b_dur, day_start_mins, day_end_mins)

    if not (a_fits_b and b_fits_a):
        # Khan - swap not possible, restore both
        mark_event_in_grid(time_grid, a_date, a_start, a_dur, buffer_mins, day_start_mins, day_end_mins)
        mark_event_in_grid(time_grid, b_date, b_start, b_dur, buffer_mins, day_start_mins, day_end_mins)
        return False

    # Khan - check if swapping improves the combined score
    before = (
        score_slot(a_date, a_start, time_grid, a_dur, buffer_mins, day_start_mins, day_end_mins) +
        score_slot(b_date, b_start, time_grid, b_dur, buffer_mins, day_start_mins, day_end_mins)
    )
    after = (
        score_slot(b_date, b_start, time_grid, a_dur, buffer_mins, day_start_mins, day_end_mins) +
        score_slot(a_date, a_start, time_grid, b_dur, buffer_mins, day_start_mins, day_end_mins)
    )

    if after > before:
        _execute_swap(flexible, i, j, a_date, a_start, a_dur, b_date, b_start, b_dur)
        mark_event_in_grid(time_grid, b_date, b_start, a_dur, buffer_mins, day_start_mins, day_end_mins)
        mark_event_in_grid(time_grid, a_date, a_start, b_dur, buffer_mins, day_start_mins, day_end_mins)
        return True

    # Khan - no improvement, restore both
    mark_event_in_grid(time_grid, a_date, a_start, a_dur, buffer_mins, day_start_mins, day_end_mins)
    mark_event_in_grid(time_grid, b_date, b_start, b_dur, buffer_mins, day_start_mins, day_end_mins)
    return False


def _run_swap_pass(flexible, time_grid, buffer_mins, day_start_mins, day_end_mins):
    # Khan - one full pass trying every pair, return True if any swap was made
    for i in range(len(flexible)):
        for j in range(i + 1, len(flexible)):
            if _try_swap_pair(flexible, i, j, time_grid, buffer_mins, day_start_mins, day_end_mins):
                return True
    return False


def run_phase3(placed_list, time_grid, constraints, max_iterations=100):
    # Khan - Improvement pass: try swapping pairs of flexible events.
    day_start_mins = time_str_to_minutes(constraints['day_start'])
    day_end_mins   = time_str_to_minutes(constraints['day_end'])
    buffer_mins    = constraints['buffer_minutes']

    flexible = [p for p in placed_list if not p.get('is_fixed', False)]
    fixed    = [p for p in placed_list if     p.get('is_fixed', False)]

    for iteration in range(max_iterations):
        if not _run_swap_pass(flexible, time_grid, buffer_mins, day_start_mins, day_end_mins):
            break

    return fixed + flexible


# =============================================================
# SECTION 7 - WEEKLY SLIDES BUILDER
# =============================================================

def _collect_events_by_date(placed_list):
    # Khan - group placed events into a dict keyed by date string
    events_by_date = defaultdict(list)
    for p in placed_list:
        if not p.get('placed_start'):
            continue
        date_str  = p['placed_start'].split('T')[0]
        start_str = p['placed_start'].split('T')[1][:5]
        end_str   = p['placed_end'].split('T')[1][:5]
        events_by_date[date_str].append({
            'title': p['event_title'],
            'start': start_str,
            'end':   end_str,
        })

    for date_str in events_by_date:
        events_by_date[date_str].sort(key=lambda e: e['start'])

    return events_by_date


def _build_week_slide(week_start, week_end, week_num, events_by_date):
    # Khan - build one week's slide dict from the events
    week_label = (
        f"Week {week_num} \u2013 "
        f"{week_start.day} {week_start.strftime('%b')} to "
        f"{week_end.day} {week_end.strftime('%b')}"
    )

    days = []
    current_d = week_start
    while current_d <= week_end:
        date_str = current_d.isoformat()
        if events_by_date[date_str]:
            day_label = f"{current_d.strftime('%A')} {current_d.day} {current_d.strftime('%b')}"
            days.append({'day': day_label, 'events': events_by_date[date_str]})
        current_d += timedelta(days=1)

    if days:
        return {'week_label': week_label, 'days': days}
    return None


def build_weekly_slides(placed_list, start_date_obj, end_date_obj):
    # Khan - Group placed events by date, then organise into weekly slides.
    events_by_date = _collect_events_by_date(placed_list)

    weeks = []
    week_start = start_date_obj
    week_num = 1

    while week_start <= end_date_obj:
        week_end = min(week_start + timedelta(days=6), end_date_obj)
        slide = _build_week_slide(week_start, week_end, week_num, events_by_date)
        if slide:
            weeks.append(slide)
        week_start = week_start + timedelta(days=7)
        week_num += 1

    return weeks


# =============================================================
# SECTION 8 - MAIN ENTRY POINT
# =============================================================

def _build_date_range(start_date_obj, end_date_obj):
    # Khan - build list of date objects from start to end inclusive
    all_dates = []
    current_d = start_date_obj
    while current_d <= end_date_obj:
        all_dates.append(current_d)
        current_d += timedelta(days=1)
    return all_dates


def _get_existing_scheduled(schedule, keep_or_erase, selected_template_ids):
    # Khan - get the existing scheduled events that block grid slots
    from student_calendar.models import ScheduleEvent
    if keep_or_erase == 'keep':
        return ScheduleEvent.objects.filter(
            schedule=schedule, status=2, placed_start__isnull=False,
        )
    return ScheduleEvent.objects.filter(
        schedule=schedule, status=2, placed_start__isnull=False,
    ).exclude(event_id__in=selected_template_ids)


def _get_instances_to_place(schedule, selected_template_ids, keep_or_erase):
    # Khan - get the instances that need to be placed
    from student_calendar.models import ScheduleEvent
    if keep_or_erase == 'keep':
        return ScheduleEvent.objects.filter(
            schedule=schedule, event_id__in=selected_template_ids, status=1,
        ).select_related('event').order_by('event_id', 'occurrence_index')
    return ScheduleEvent.objects.filter(
        schedule=schedule, event_id__in=selected_template_ids, status__in=[1, 2],
    ).select_related('event').order_by('event_id', 'occurrence_index')


def _group_instances_by_template(instances_qs):
    # Khan - group ScheduleEvent rows into a dict keyed by event_id
    instances_by_template = defaultdict(list)
    for se in instances_qs:
        instances_by_template[se.event_id].append({
            'id':               se.id,
            'occurrence_index': se.occurrence_index,
            'fixed_start':      se.event.start.isoformat() if se.event.start else None,
            'fixed_end':        se.event.end.isoformat()   if se.event.end   else None,
        })
    return instances_by_template


def _build_template_data(t, instances_by_template):
    # Khan - build a template data dict from an Event model instance
    if t.duration:
        dur_mins = t.duration
        is_fixed = False
    elif t.start and t.end:
        dur_mins = int((t.end - t.start).total_seconds() / 60)
        is_fixed = True
    else:
        dur_mins = 60
        is_fixed = False

    return {
        'id':               t.id,
        'title':            t.title,
        'importance':       t.importance,
        'repeat_days':      t.repeat_days or 0,
        'duration_minutes': dur_mins,
        'is_fixed':         is_fixed,
        'created_count':    len(instances_by_template.get(t.id, [])),
    }


def _build_summary(fixed_templates, flexible_templates, placed_list, instances_by_template):
    # Khan - build the per-template summary dict
    summary_by_template = {}
    for t in fixed_templates + flexible_templates:
        summary_by_template[t['id']] = {
            'title':  t['title'],
            'placed': 0,
            'total':  len(instances_by_template.get(t['id'], [])),
        }
    for p in placed_list:
        tid = p.get('template_id')
        if tid in summary_by_template:
            summary_by_template[tid]['placed'] += 1
    return summary_by_template


def run_smart_planner(user, constraints, selected_template_ids):
    # Khan - Main entry point for the entire smart planner.
    from student_calendar.models import ScheduleEvent, Event, UserSchedule

    start_date_obj = date.fromisoformat(constraints['start_date'])
    end_date_obj   = date.fromisoformat(constraints['end_date'])
    buffer_mins    = constraints['buffer_minutes']
    keep_or_erase  = constraints.get('keep_or_erase', 'keep')

    user_schedule = UserSchedule.objects.filter(user=user).first()
    if not user_schedule:
        return {'error': 'No schedule found for this user'}
    schedule = user_schedule.schedule

    all_dates = _build_date_range(start_date_obj, end_date_obj)
    existing_scheduled = _get_existing_scheduled(schedule, keep_or_erase, selected_template_ids)
    time_grid = build_time_grid(all_dates, existing_scheduled, constraints['day_start'], constraints['day_end'], buffer_mins)

    instances_qs = _get_instances_to_place(schedule, selected_template_ids, keep_or_erase)
    instances_by_template = _group_instances_by_template(instances_qs)

    # Khan - build template data and separate fixed from flexible
    templates_qs = Event.objects.filter(id__in=selected_template_ids, user=user)
    fixed_templates = []
    flexible_templates = []
    for t in templates_qs:
        tdata = _build_template_data(t, instances_by_template)
        if tdata['is_fixed']:
            fixed_templates.append(tdata)
        else:
            flexible_templates.append(tdata)

    # Khan - Phase 1: score and rank flexible templates
    selected_days_bitmask = constraints['selected_days_bitmask']
    for t in flexible_templates:
        t['_priority'] = score_template(t, flexible_templates, selected_days_bitmask)
    flexible_templates.sort(key=lambda t: t['_priority'], reverse=True)

    # Khan - build ordered list: fixed first, then flexible by priority
    ordered = []
    for t in fixed_templates:
        ordered.append((t, instances_by_template.get(t['id'], [])))
    for t in flexible_templates:
        ordered.append((t, instances_by_template.get(t['id'], [])))

    # Khan - Phase 2 + 3: place then improve
    placed_list, unplaced_list = run_phase2(ordered, time_grid, constraints)
    placed_list = run_phase3(placed_list, time_grid, constraints)

    summary_by_template = _build_summary(fixed_templates, flexible_templates, placed_list, instances_by_template)
    weeks = build_weekly_slides(placed_list, start_date_obj, end_date_obj)

    return {
        'placed':   placed_list,
        'unplaced': unplaced_list,
        'summary': {
            'total_placed':   len(placed_list),
            'total_unplaced': len(unplaced_list),
            'by_template':    list(summary_by_template.values()),
        },
        'weeks': weeks,
    }
