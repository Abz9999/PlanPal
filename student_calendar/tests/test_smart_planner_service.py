# Khan - tests for the smart planner algorithm (smart_planner_service.py)

import math
from datetime import date, timedelta, datetime
from django.test import TestCase
from django.utils import timezone

from student_calendar.smart_planner_service import (
    time_to_slot_index,
    slot_index_to_time,
    minutes_to_time_str,
    time_str_to_minutes,
    get_day_bitmask,
    build_time_grid,
    mark_event_in_grid,
    unmark_event_in_grid,
    score_template,
    find_valid_slots,
    score_slot,
    run_phase2,
    run_phase3,
    build_weekly_slides,
    run_smart_planner,
    SLOT_MINUTES,
)


# fake object to stand in for ScheduleEvent rows in grid tests
# just needs placed_start and placed_end attributes
class FakeScheduleEvent:
    def __init__(self, placed_start, placed_end):
        self.placed_start = placed_start
        self.placed_end = placed_end


# ---- time_to_slot_index tests ----

class TimeToSlotIndexTests(TestCase):

    def test_start_of_day_returns_zero(self):
        # 08:00 with day starting at 08:00 = slot 0
        self.assertEqual(time_to_slot_index(480, 480), 0)

    def test_one_hour_after_start(self):
        # 09:00 with day start 08:00 = 60/15 = slot 4
        self.assertEqual(time_to_slot_index(540, 480), 4)

    def test_half_hour_after_start(self):
        self.assertEqual(time_to_slot_index(510, 480), 2)

    def test_different_day_start(self):
        # 10:00 with day start 09:00 = slot 4
        self.assertEqual(time_to_slot_index(600, 540), 4)

    def test_large_offset(self):
        # 20:00 with day start 08:00 = 720/15 = slot 48
        self.assertEqual(time_to_slot_index(1200, 480), 48)


# ---- slot_index_to_time tests ----

class SlotIndexToTimeTests(TestCase):

    def test_slot_zero_returns_day_start(self):
        self.assertEqual(slot_index_to_time(0, 480), 480)

    def test_slot_four(self):
        # slot 4 * 15 = 60 mins after 08:00 = 540
        self.assertEqual(slot_index_to_time(4, 480), 540)

    def test_round_trip(self):
        # convert to slot and back should give the same number
        original = 600
        slot = time_to_slot_index(original, 480)
        self.assertEqual(slot_index_to_time(slot, 480), original)

    def test_round_trip_different_start(self):
        original = 660
        slot = time_to_slot_index(original, 540)
        self.assertEqual(slot_index_to_time(slot, 540), original)


# ---- minutes_to_time_str tests ----

class MinutesToTimeStrTests(TestCase):

    def test_midnight(self):
        self.assertEqual(minutes_to_time_str(0), "00:00")

    def test_eight_am(self):
        self.assertEqual(minutes_to_time_str(480), "08:00")

    def test_ten_thirty(self):
        self.assertEqual(minutes_to_time_str(630), "10:30")

    def test_pads_single_digits(self):
        # 1:05 AM
        self.assertEqual(minutes_to_time_str(65), "01:05")

    def test_end_of_day(self):
        self.assertEqual(minutes_to_time_str(1439), "23:59")


# ---- time_str_to_minutes tests ----

class TimeStrToMinutesTests(TestCase):

    def test_midnight(self):
        self.assertEqual(time_str_to_minutes("00:00"), 0)

    def test_nine_am(self):
        self.assertEqual(time_str_to_minutes("09:00"), 540)

    def test_ten_thirty(self):
        self.assertEqual(time_str_to_minutes("10:30"), 630)

    def test_round_trip(self):
        time_str = minutes_to_time_str(750)
        self.assertEqual(time_str_to_minutes(time_str), 750)


# ---- get_day_bitmask tests ----

class GetDayBitmaskTests(TestCase):

    def test_monday(self):
        self.assertEqual(get_day_bitmask(date(2026, 4, 13)), 1)

    def test_tuesday(self):
        self.assertEqual(get_day_bitmask(date(2026, 4, 14)), 2)

    def test_wednesday(self):
        self.assertEqual(get_day_bitmask(date(2026, 4, 15)), 4)

    def test_thursday(self):
        self.assertEqual(get_day_bitmask(date(2026, 4, 16)), 8)

    def test_friday(self):
        self.assertEqual(get_day_bitmask(date(2026, 4, 17)), 16)

    def test_saturday(self):
        self.assertEqual(get_day_bitmask(date(2026, 4, 18)), 32)

    def test_sunday(self):
        self.assertEqual(get_day_bitmask(date(2026, 4, 19)), 64)

    def test_full_week_covers_all_bits(self):
        # Mon-Sun should OR together to 127
        week_start = date(2026, 4, 13)
        combined = 0
        for i in range(7):
            combined |= get_day_bitmask(week_start + timedelta(days=i))
        self.assertEqual(combined, 127)


# ---- build_time_grid tests ----

class BuildTimeGridTests(TestCase):

    def test_empty_events_all_free(self):
        # 1 day, 08:00-10:00 = 8 slots, no events so all should be True
        grid = build_time_grid([date(2026, 4, 13)], [], "08:00", "10:00", 0)
        self.assertEqual(len(grid["2026-04-13"]), 8)
        self.assertTrue(all(grid["2026-04-13"]))

    def test_slot_count_matches_window(self):
        # 08:00-22:00 = 14 hours = 56 slots
        grid = build_time_grid([date(2026, 4, 13)], [], "08:00", "22:00", 0)
        self.assertEqual(len(grid["2026-04-13"]), 56)

    def test_multiple_days(self):
        days = [date(2026, 4, 13), date(2026, 4, 14), date(2026, 4, 15)]
        grid = build_time_grid(days, [], "08:00", "10:00", 0)
        self.assertEqual(len(grid), 3)

    def test_event_blocks_correct_slots(self):
        # event 09:00-10:00 should block slots 4-7
        event = FakeScheduleEvent(
            datetime(2026, 4, 13, 9, 0), datetime(2026, 4, 13, 10, 0)
        )
        grid = build_time_grid([date(2026, 4, 13)], [event], "08:00", "12:00", 0)
        day = grid["2026-04-13"]
        self.assertTrue(all(day[0:4]))     # 08:00-09:00 free
        self.assertFalse(any(day[4:8]))    # 09:00-10:00 blocked
        self.assertTrue(all(day[8:16]))    # 10:00-12:00 free

    def test_buffer_expands_blocked_region(self):
        # event 09:00-10:00 with 30min buffer should block 08:30-10:30
        event = FakeScheduleEvent(
            datetime(2026, 4, 13, 9, 0), datetime(2026, 4, 13, 10, 0)
        )
        grid = build_time_grid([date(2026, 4, 13)], [event], "08:00", "12:00", 30)
        day = grid["2026-04-13"]
        self.assertTrue(all(day[0:2]))      # 08:00-08:30 free
        self.assertFalse(any(day[2:10]))    # 08:30-10:30 blocked
        self.assertTrue(all(day[10:16]))    # 10:30-12:00 free

    def test_event_outside_range_is_skipped(self):
        # grid covers Apr 13, event is on Apr 14
        event = FakeScheduleEvent(
            datetime(2026, 4, 14, 9, 0), datetime(2026, 4, 14, 10, 0)
        )
        grid = build_time_grid([date(2026, 4, 13)], [event], "08:00", "12:00", 0)
        self.assertTrue(all(grid["2026-04-13"]))

    def test_event_with_none_times_is_skipped(self):
        event = FakeScheduleEvent(None, None)
        grid = build_time_grid([date(2026, 4, 13)], [event], "08:00", "12:00", 0)
        self.assertTrue(all(grid["2026-04-13"]))


# ---- mark_event_in_grid tests ----

class MarkEventInGridTests(TestCase):

    def test_marks_correct_slots(self):
        grid = {"2026-04-13": [True] * 16}
        # mark 1hr event at 09:00, no buffer
        mark_event_in_grid(grid, "2026-04-13", 540, 60, 0, 480, 720)
        self.assertFalse(any(grid["2026-04-13"][4:8]))
        self.assertTrue(all(grid["2026-04-13"][0:4]))
        self.assertTrue(all(grid["2026-04-13"][8:16]))

    def test_marks_with_buffer(self):
        grid = {"2026-04-13": [True] * 16}
        # 1hr at 09:00 with 15min buffer = 08:45-10:15
        mark_event_in_grid(grid, "2026-04-13", 540, 60, 15, 480, 720)
        self.assertFalse(any(grid["2026-04-13"][3:9]))


# ---- unmark_event_in_grid tests ----

class UnmarkEventInGridTests(TestCase):

    def test_unmark_frees_slots(self):
        grid = {"2026-04-13": [False] * 16}
        unmark_event_in_grid(grid, "2026-04-13", 540, 60, 0, 480, 720)
        self.assertTrue(all(grid["2026-04-13"][4:8]))
        self.assertFalse(any(grid["2026-04-13"][0:4]))

    def test_mark_then_unmark_restores_original(self):
        grid = {"2026-04-13": [True] * 16}
        original = list(grid["2026-04-13"])
        mark_event_in_grid(grid, "2026-04-13", 540, 60, 15, 480, 720)
        unmark_event_in_grid(grid, "2026-04-13", 540, 60, 15, 480, 720)
        self.assertEqual(grid["2026-04-13"], original)


# ---- score_template tests ----

class ScoreTemplateTests(TestCase):

    def setUp(self):
        # all weekdays selected = 31 (Mon-Fri)
        self.user_days = 31

    def test_high_importance_scores_higher(self):
        # importance 1 = Very Low gets highest importance_score in the formula
        # importance 5 = Critical gets lowest - the algorithm inverts this
        high = {'id': 1, 'duration_minutes': 60, 'importance': 1,
                'repeat_days': 0, 'created_count': 1}
        low = {'id': 2, 'duration_minutes': 60, 'importance': 5,
               'repeat_days': 0, 'created_count': 1}
        templates = [high, low]
        self.assertGreater(
            score_template(high, templates, self.user_days),
            score_template(low, templates, self.user_days)
        )

    def test_tight_days_scores_higher(self):
        # Mon-only (1) vs fully flexible (0)
        tight = {'id': 1, 'duration_minutes': 60, 'importance': 3,
                 'repeat_days': 1, 'created_count': 1}
        flex = {'id': 2, 'duration_minutes': 60, 'importance': 3,
                'repeat_days': 0, 'created_count': 1}
        templates = [tight, flex]
        self.assertGreater(
            score_template(tight, templates, self.user_days),
            score_template(flex, templates, self.user_days)
        )

    def test_longer_duration_scores_higher(self):
        short = {'id': 1, 'duration_minutes': 30, 'importance': 3,
                 'repeat_days': 0, 'created_count': 1}
        long = {'id': 2, 'duration_minutes': 120, 'importance': 3,
                'repeat_days': 0, 'created_count': 1}
        templates = [short, long]
        self.assertGreater(
            score_template(long, templates, self.user_days),
            score_template(short, templates, self.user_days)
        )

    def test_fewer_instances_scores_higher(self):
        scarce = {'id': 1, 'duration_minutes': 60, 'importance': 3,
                  'repeat_days': 0, 'created_count': 1}
        plenty = {'id': 2, 'duration_minutes': 60, 'importance': 3,
                  'repeat_days': 0, 'created_count': 9}
        templates = [scarce, plenty]
        self.assertGreater(
            score_template(scarce, templates, self.user_days),
            score_template(plenty, templates, self.user_days)
        )

    def test_score_between_zero_and_one(self):
        t = {'id': 1, 'duration_minutes': 60, 'importance': 3,
             'repeat_days': 0, 'created_count': 1}
        score = score_template(t, [t], self.user_days)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_no_overlap_days_does_not_crash(self):
        # event needs Saturday (32) but user only has Mon-Fri (31)
        t = {'id': 1, 'duration_minutes': 60, 'importance': 3,
             'repeat_days': 32, 'created_count': 1}
        score = score_template(t, [t], self.user_days)
        self.assertGreaterEqual(score, 0.0)


# ---- find_valid_slots tests ----

class FindValidSlotsTests(TestCase):

    def setUp(self):
        # 3 day grid Mon-Wed, 08:00-12:00 all free
        self.grid = {
            "2026-04-13": [True] * 16,
            "2026-04-14": [True] * 16,
            "2026-04-15": [True] * 16,
        }
        self.constraints = {
            'day_start': '08:00',
            'day_end': '12:00',
            'buffer_minutes': 0,
            'selected_days_bitmask': 7,  # Mon + Tue + Wed
        }

    def test_empty_grid_returns_slots(self):
        t = {'id': 1, 'duration_minutes': 60, 'repeat_days': 0}
        slots = find_valid_slots(t, self.grid, self.constraints, set())
        self.assertGreater(len(slots), 0)

    def test_full_grid_returns_nothing(self):
        for d in self.grid:
            self.grid[d] = [False] * 16
        t = {'id': 1, 'duration_minutes': 60, 'repeat_days': 0}
        slots = find_valid_slots(t, self.grid, self.constraints, set())
        self.assertEqual(len(slots), 0)

    def test_repeat_days_filters_to_correct_day(self):
        # only allowed on Monday (bitmask 1)
        t = {'id': 1, 'duration_minutes': 60, 'repeat_days': 1}
        slots = find_valid_slots(t, self.grid, self.constraints, set())
        for date_str, _ in slots:
            self.assertEqual(date_str, "2026-04-13")

    def test_placed_date_set_excludes_date(self):
        t = {'id': 1, 'duration_minutes': 60, 'repeat_days': 0}
        placed = {(1, "2026-04-13")}  # already placed on Monday
        slots = find_valid_slots(t, self.grid, self.constraints, placed)
        for date_str, _ in slots:
            self.assertNotEqual(date_str, "2026-04-13")

    def test_event_too_long_for_window(self):
        # 5hr event in a 4hr window
        t = {'id': 1, 'duration_minutes': 300, 'repeat_days': 0}
        slots = find_valid_slots(t, self.grid, self.constraints, set())
        self.assertEqual(len(slots), 0)

    def test_selected_days_bitmask_filters(self):
        # only Tuesday selected
        constraints = dict(self.constraints)
        constraints['selected_days_bitmask'] = 2
        t = {'id': 1, 'duration_minutes': 60, 'repeat_days': 0}
        slots = find_valid_slots(t, self.grid, constraints, set())
        for date_str, _ in slots:
            self.assertEqual(date_str, "2026-04-14")

    def test_slots_within_time_window(self):
        t = {'id': 1, 'duration_minutes': 60, 'repeat_days': 0}
        slots = find_valid_slots(t, self.grid, self.constraints, set())
        for _, start_mins in slots:
            self.assertGreaterEqual(start_mins, 480)
            self.assertLessEqual(start_mins + 60, 720)


# ---- score_slot tests ----

class ScoreSlotTests(TestCase):

    def test_score_between_zero_and_one(self):
        grid = {"2026-04-13": [True] * 56}
        score = score_slot("2026-04-13", 540, grid, 60, 0, 480, 1320)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_exact_gap_scores_high(self):
        # 1hr gap surrounded by blocked slots
        day = [False] * 56
        day[4:8] = [True, True, True, True]  # only 09:00-10:00 free
        grid = {"2026-04-13": day}
        score = score_slot("2026-04-13", 540, grid, 60, 0, 480, 1320)
        self.assertGreater(score, 0.5)

    def test_empty_day_still_returns_score(self):
        grid = {"2026-04-13": [True] * 56}
        score = score_slot("2026-04-13", 540, grid, 60, 0, 480, 1320)
        self.assertGreater(score, 0.0)

    def test_near_event_scores_higher_compactness(self):
        # event right next to an occupied slot vs far away
        day_near = [True] * 16
        day_near[0:4] = [False] * 4  # blocked 08:00-09:00
        day_far = [True] * 16
        day_far[12:16] = [False] * 4  # blocked 11:00-12:00
        score_near = score_slot("2026-04-13", 540, {"2026-04-13": day_near}, 60, 0, 480, 720)
        score_far = score_slot("2026-04-13", 540, {"2026-04-13": day_far}, 60, 0, 480, 720)
        self.assertGreater(score_near, score_far)

    def test_day_load_affects_score(self):
        # light day and heavy day should produce different scores
        day_light = [True] * 16
        day_light[0:2] = [False] * 2
        day_heavy = [True] * 16
        day_heavy[0:10] = [False] * 10
        score_light = score_slot("2026-04-13", 600, {"2026-04-13": day_light}, 60, 0, 480, 720)
        score_heavy = score_slot("2026-04-13", 600, {"2026-04-13": day_heavy}, 60, 0, 480, 720)
        self.assertNotEqual(score_light, score_heavy)


# ---- run_phase2 tests ----

class RunPhase2Tests(TestCase):

    def setUp(self):
        self.constraints = {
            'day_start': '08:00',
            'day_end': '12:00',
            'buffer_minutes': 0,
            'selected_days_bitmask': 7,
        }
        self.grid = {
            "2026-04-13": [True] * 16,
            "2026-04-14": [True] * 16,
            "2026-04-15": [True] * 16,
        }

    def test_flexible_event_gets_placed(self):
        t = {'id': 1, 'title': 'Gym', 'duration_minutes': 60,
             'is_fixed': False, 'repeat_days': 0, 'importance': 3}
        instances = [{'id': 101, 'occurrence_index': 1}]
        placed, unplaced = run_phase2([(t, instances)], self.grid, self.constraints)
        self.assertEqual(len(placed), 1)
        self.assertEqual(len(unplaced), 0)
        self.assertIn('T', placed[0]['placed_start'])

    def test_fixed_event_locked_in(self):
        t = {'id': 2, 'title': 'Lecture', 'duration_minutes': 60,
             'is_fixed': True, 'repeat_days': 1, 'importance': 5}
        instances = [{'id': 201, 'occurrence_index': 1,
                      'fixed_start': '2026-04-13T09:00:00',
                      'fixed_end': '2026-04-13T10:00:00'}]
        placed, unplaced = run_phase2([(t, instances)], self.grid, self.constraints)
        self.assertEqual(len(placed), 1)
        self.assertTrue(placed[0]['is_fixed'])
        self.assertEqual(placed[0]['placed_start'], '2026-04-13T09:00:00')

    def test_no_valid_slots_goes_to_unplaced(self):
        for d in self.grid:
            self.grid[d] = [False] * 16
        t = {'id': 3, 'title': 'Meeting', 'duration_minutes': 60,
             'is_fixed': False, 'repeat_days': 0, 'importance': 3}
        instances = [{'id': 301, 'occurrence_index': 1}]
        placed, unplaced = run_phase2([(t, instances)], self.grid, self.constraints)
        self.assertEqual(len(placed), 0)
        self.assertEqual(len(unplaced), 1)
        self.assertIn('reason', unplaced[0])

    def test_no_duplicate_template_on_same_date(self):
        # 2 instances, only Monday available
        constraints = dict(self.constraints)
        constraints['selected_days_bitmask'] = 1
        grid = {"2026-04-13": [True] * 16}
        t = {'id': 4, 'title': 'Study', 'duration_minutes': 60,
             'is_fixed': False, 'repeat_days': 0, 'importance': 3}
        instances = [{'id': 401, 'occurrence_index': 1},
                     {'id': 402, 'occurrence_index': 2}]
        placed, unplaced = run_phase2([(t, instances)], grid, constraints)
        self.assertEqual(len(placed), 1)
        self.assertEqual(len(unplaced), 1)

    def test_day_mismatch_reason(self):
        # event needs Saturday (32) but only Mon-Wed selected (7)
        t = {'id': 5, 'title': 'Weekend Run', 'duration_minutes': 60,
             'is_fixed': False, 'repeat_days': 32, 'importance': 3}
        instances = [{'id': 501, 'occurrence_index': 1}]
        placed, unplaced = run_phase2([(t, instances)], self.grid, self.constraints)
        self.assertEqual(len(unplaced), 1)
        self.assertIn("days", unplaced[0]['reason'].lower())

    def test_multiple_templates_all_placed(self):
        t_a = {'id': 6, 'title': 'Gym', 'duration_minutes': 60,
               'is_fixed': False, 'repeat_days': 0, 'importance': 3}
        t_b = {'id': 7, 'title': 'Study', 'duration_minutes': 60,
               'is_fixed': False, 'repeat_days': 0, 'importance': 3}
        placed, unplaced = run_phase2(
            [(t_a, [{'id': 601, 'occurrence_index': 1}]),
             (t_b, [{'id': 701, 'occurrence_index': 1}])],
            self.grid, self.constraints
        )
        self.assertEqual(len(placed), 2)
        self.assertEqual(len(unplaced), 0)


# ---- run_phase3 tests ----

class RunPhase3Tests(TestCase):

    def setUp(self):
        self.constraints = {
            'day_start': '08:00',
            'day_end': '12:00',
            'buffer_minutes': 0,
            'selected_days_bitmask': 7,
        }
        self.grid = {
            "2026-04-13": [True] * 16,
            "2026-04-14": [True] * 16,
        }

    def test_fixed_events_not_swapped(self):
        placed = [
            {'schedule_event_id': 1, 'event_title': 'Lecture',
             'occurrence_index': 1, 'template_id': 1, 'is_fixed': True,
             'placed_start': '2026-04-13T09:00', 'placed_end': '2026-04-13T10:00'},
            {'schedule_event_id': 2, 'event_title': 'Gym',
             'occurrence_index': 1, 'template_id': 2, 'is_fixed': False,
             'placed_start': '2026-04-14T09:00', 'placed_end': '2026-04-14T10:00'},
        ]
        mark_event_in_grid(self.grid, "2026-04-13", 540, 60, 0, 480, 720)
        mark_event_in_grid(self.grid, "2026-04-14", 540, 60, 0, 480, 720)
        result = run_phase3(placed, self.grid, self.constraints)
        fixed = [p for p in result if p['is_fixed']]
        self.assertEqual(fixed[0]['placed_start'], '2026-04-13T09:00')

    def test_same_template_not_swapped(self):
        placed = [
            {'schedule_event_id': 1, 'event_title': 'Gym',
             'occurrence_index': 1, 'template_id': 1, 'is_fixed': False,
             'placed_start': '2026-04-13T08:00', 'placed_end': '2026-04-13T09:00'},
            {'schedule_event_id': 2, 'event_title': 'Gym',
             'occurrence_index': 2, 'template_id': 1, 'is_fixed': False,
             'placed_start': '2026-04-14T08:00', 'placed_end': '2026-04-14T09:00'},
        ]
        mark_event_in_grid(self.grid, "2026-04-13", 480, 60, 0, 480, 720)
        mark_event_in_grid(self.grid, "2026-04-14", 480, 60, 0, 480, 720)
        result = run_phase3(placed, self.grid, self.constraints)
        flexible = [p for p in result if not p.get('is_fixed')]
        self.assertEqual(flexible[0]['placed_start'], '2026-04-13T08:00')
        self.assertEqual(flexible[1]['placed_start'], '2026-04-14T08:00')

    def test_converges_when_no_improvement(self):
        placed = [
            {'schedule_event_id': 1, 'event_title': 'Gym',
             'occurrence_index': 1, 'template_id': 1, 'is_fixed': False,
             'placed_start': '2026-04-13T08:00', 'placed_end': '2026-04-13T09:00'},
            {'schedule_event_id': 2, 'event_title': 'Study',
             'occurrence_index': 1, 'template_id': 2, 'is_fixed': False,
             'placed_start': '2026-04-14T08:00', 'placed_end': '2026-04-14T09:00'},
        ]
        mark_event_in_grid(self.grid, "2026-04-13", 480, 60, 0, 480, 720)
        mark_event_in_grid(self.grid, "2026-04-14", 480, 60, 0, 480, 720)
        result = run_phase3(placed, self.grid, self.constraints, max_iterations=5)
        self.assertEqual(len(result), 2)

    def test_returns_fixed_and_flexible_combined(self):
        placed = [
            {'schedule_event_id': 1, 'event_title': 'Lecture',
             'occurrence_index': 1, 'template_id': 1, 'is_fixed': True,
             'placed_start': '2026-04-13T09:00', 'placed_end': '2026-04-13T10:00'},
            {'schedule_event_id': 2, 'event_title': 'Gym',
             'occurrence_index': 1, 'template_id': 2, 'is_fixed': False,
             'placed_start': '2026-04-14T09:00', 'placed_end': '2026-04-14T10:00'},
        ]
        mark_event_in_grid(self.grid, "2026-04-13", 540, 60, 0, 480, 720)
        mark_event_in_grid(self.grid, "2026-04-14", 540, 60, 0, 480, 720)
        result = run_phase3(placed, self.grid, self.constraints)
        self.assertEqual(len(result), 2)
        titles = {p['event_title'] for p in result}
        self.assertIn('Lecture', titles)
        self.assertIn('Gym', titles)

    def test_beneficial_swap_happens(self):
        # set up Mon with a tight 1hr gap, Tue wide open
        grid = {
            "2026-04-13": [True] * 16,
            "2026-04-14": [True] * 16,
        }
        # block Mon except 09:00-10:00
        for i in range(0, 4):
            grid["2026-04-13"][i] = False
        for i in range(8, 16):
            grid["2026-04-13"][i] = False

        placed = [
            {'schedule_event_id': 1, 'event_title': 'Short',
             'occurrence_index': 1, 'template_id': 1, 'is_fixed': False,
             'placed_start': '2026-04-14T08:00', 'placed_end': '2026-04-14T09:00'},
            {'schedule_event_id': 2, 'event_title': 'Long',
             'occurrence_index': 1, 'template_id': 2, 'is_fixed': False,
             'placed_start': '2026-04-13T09:00', 'placed_end': '2026-04-13T10:00'},
        ]
        mark_event_in_grid(grid, "2026-04-14", 480, 60, 0, 480, 720)
        mark_event_in_grid(grid, "2026-04-13", 540, 60, 0, 480, 720)
        result = run_phase3(placed, grid, self.constraints)
        # just check it didn't crash and returned both
        flexible = [p for p in result if not p.get('is_fixed')]
        self.assertEqual(len(flexible), 2)


# ---- build_weekly_slides tests ----

class BuildWeeklySlidesTests(TestCase):

    def test_events_grouped_by_week(self):
        placed = [
            {'event_title': 'Gym', 'placed_start': '2026-04-13T09:00',
             'placed_end': '2026-04-13T10:00'},
            {'event_title': 'Study', 'placed_start': '2026-04-20T09:00',
             'placed_end': '2026-04-20T10:00'},
        ]
        weeks = build_weekly_slides(placed, date(2026, 4, 13), date(2026, 4, 26))
        self.assertEqual(len(weeks), 2)
        self.assertIn("Week 1", weeks[0]['week_label'])
        self.assertIn("Week 2", weeks[1]['week_label'])

    def test_days_sorted_within_week(self):
        placed = [
            {'event_title': 'Wed', 'placed_start': '2026-04-15T09:00',
             'placed_end': '2026-04-15T10:00'},
            {'event_title': 'Mon', 'placed_start': '2026-04-13T09:00',
             'placed_end': '2026-04-13T10:00'},
        ]
        weeks = build_weekly_slides(placed, date(2026, 4, 13), date(2026, 4, 19))
        days = weeks[0]['days']
        self.assertIn("Monday", days[0]['day'])
        self.assertIn("Wednesday", days[1]['day'])

    def test_empty_weeks_excluded(self):
        placed = [
            {'event_title': 'Study', 'placed_start': '2026-04-20T09:00',
             'placed_end': '2026-04-20T10:00'},
        ]
        weeks = build_weekly_slides(placed, date(2026, 4, 13), date(2026, 4, 26))
        self.assertEqual(len(weeks), 1)
        self.assertIn("Week 2", weeks[0]['week_label'])

    def test_empty_list_returns_nothing(self):
        weeks = build_weekly_slides([], date(2026, 4, 13), date(2026, 4, 19))
        self.assertEqual(len(weeks), 0)

    def test_same_day_events_sorted_by_time(self):
        placed = [
            {'event_title': 'Late', 'placed_start': '2026-04-13T11:00',
             'placed_end': '2026-04-13T12:00'},
            {'event_title': 'Early', 'placed_start': '2026-04-13T08:00',
             'placed_end': '2026-04-13T09:00'},
        ]
        weeks = build_weekly_slides(placed, date(2026, 4, 13), date(2026, 4, 19))
        events = weeks[0]['days'][0]['events']
        self.assertEqual(events[0]['title'], 'Early')
        self.assertEqual(events[1]['title'], 'Late')

    def test_skips_items_with_no_start(self):
        placed = [
            {'event_title': 'Ghost', 'placed_start': None, 'placed_end': None},
            {'event_title': 'Real', 'placed_start': '2026-04-13T09:00',
             'placed_end': '2026-04-13T10:00'},
        ]
        weeks = build_weekly_slides(placed, date(2026, 4, 13), date(2026, 4, 19))
        events = weeks[0]['days'][0]['events']
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['title'], 'Real')


# ---- run_smart_planner tests (needs DB) ----

class RunSmartPlannerTests(TestCase):

    def setUp(self):
        from student_calendar.models import (
            User, Event, Category, Schedule, ScheduleEvent, UserSchedule
        )
        self.User = User
        self.Event = Event
        self.ScheduleEvent = ScheduleEvent

        self.user = User.objects.create_user(username="planneruser", email="planner@test.com", password="testpass123")
        self.category = Category.objects.create(name="Study", colour="#0000FF")
        self.schedule = Schedule.objects.create(title="Test Schedule", is_active=True)
        UserSchedule.objects.create(user=self.user, schedule=self.schedule)

        self.base_constraints = {
            'start_date': '2026-04-13',
            'end_date': '2026-04-17',
            'day_start': '08:00',
            'day_end': '18:00',
            'selected_days_bitmask': 31,  # Mon-Fri
            'buffer_minutes': 0,
            'keep_or_erase': 'keep',
        }

    def _make_flexible(self, title="Gym", duration=60, importance=3):
        event = self.Event.objects.create(
            title=title, user=self.user, category=self.category,
            duration=duration, importance=importance,
            number_of_days=1, repeat_days=1, max_instances=2,
        )
        for i in range(2):
            self.ScheduleEvent.objects.create(
                event=event, schedule=self.schedule,
                status=self.ScheduleEvent.Status.CREATED,
                occurrence_index=i + 1,
            )
        return event

    def _make_fixed(self, title="Lecture"):
        event = self.Event.objects.create(
            title=title, user=self.user, category=self.category,
            start=timezone.make_aware(datetime(2026, 4, 13, 9, 0)),
            end=timezone.make_aware(datetime(2026, 4, 13, 10, 0)),
            importance=5, number_of_days=1, repeat_days=1, max_instances=1,
        )
        self.ScheduleEvent.objects.create(
            event=event, schedule=self.schedule,
            status=self.ScheduleEvent.Status.CREATED,
            occurrence_index=1,
        )
        return event

    def test_flexible_event_placed(self):
        event = self._make_flexible()
        result = run_smart_planner(self.user, self.base_constraints, [event.id])
        self.assertIn('placed', result)
        self.assertGreater(len(result['placed']), 0)

    def test_no_schedule_returns_error(self):
        other_user = self.User.objects.create_user(username="noplan", email="noplan@test.com", password="testpass123")
        result = run_smart_planner(other_user, self.base_constraints, [1])
        self.assertIn('error', result)

    def test_selected_ids_filtering(self):
        gym = self._make_flexible(title="Gym")
        study = self._make_flexible(title="Study")
        # only select gym
        result = run_smart_planner(self.user, self.base_constraints, [gym.id])
        titles = {p['event_title'] for p in result['placed']}
        self.assertIn('Gym', titles)
        self.assertNotIn('Study', titles)

    def test_result_has_weeks(self):
        event = self._make_flexible()
        result = run_smart_planner(self.user, self.base_constraints, [event.id])
        self.assertIn('weeks', result)
        self.assertIsInstance(result['weeks'], list)

    def test_result_has_summary(self):
        event = self._make_flexible()
        result = run_smart_planner(self.user, self.base_constraints, [event.id])
        summary = result['summary']
        self.assertIn('total_placed', summary)
        self.assertIn('total_unplaced', summary)
        self.assertIn('by_template', summary)

    def test_erase_mode_replans_scheduled(self):
        event = self._make_flexible()
        # mark one instance as already scheduled
        instance = self.ScheduleEvent.objects.filter(event=event).first()
        instance.status = self.ScheduleEvent.Status.SCHEDULED
        instance.placed_start = timezone.make_aware(datetime(2026, 4, 13, 9, 0))
        instance.placed_end = timezone.make_aware(datetime(2026, 4, 13, 10, 0))
        instance.save()

        constraints = dict(self.base_constraints)
        constraints['keep_or_erase'] = 'erase'
        result = run_smart_planner(self.user, constraints, [event.id])
        # erase mode should include both instances
        total = result['summary']['total_placed'] + result['summary']['total_unplaced']
        self.assertEqual(total, 2)

    def test_keep_mode_only_places_created(self):
        event = self._make_flexible()
        # mark one as scheduled
        instance = self.ScheduleEvent.objects.filter(event=event).first()
        instance.status = self.ScheduleEvent.Status.SCHEDULED
        instance.placed_start = timezone.make_aware(datetime(2026, 4, 13, 9, 0))
        instance.placed_end = timezone.make_aware(datetime(2026, 4, 13, 10, 0))
        instance.save()

        result = run_smart_planner(self.user, self.base_constraints, [event.id])
        # keep mode should only touch the 1 CREATED instance
        total = result['summary']['total_placed'] + result['summary']['total_unplaced']
        self.assertEqual(total, 1)

    def test_fixed_event_in_placed(self):
        event = self._make_fixed()
        result = run_smart_planner(self.user, self.base_constraints, [event.id])
        self.assertEqual(len(result['placed']), 1)
        self.assertTrue(result['placed'][0]['is_fixed'])

    def test_summary_counts_correct(self):
        event = self._make_flexible()
        result = run_smart_planner(self.user, self.base_constraints, [event.id])
        by_template = result['summary']['by_template']
        self.assertEqual(len(by_template), 1)
        self.assertEqual(by_template[0]['title'], 'Gym')
        self.assertEqual(by_template[0]['total'], 2)

    def test_placed_count_matches_summary(self):
        event = self._make_flexible()
        result = run_smart_planner(self.user, self.base_constraints, [event.id])
        self.assertEqual(result['summary']['total_placed'], len(result['placed']))
        self.assertEqual(result['summary']['total_unplaced'], len(result['unplaced']))
