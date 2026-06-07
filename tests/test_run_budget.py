import unittest

from src.runtime.run_budget import RunBudget


class RunBudgetTest(unittest.TestCase):
    def test_no_continuation_when_run_finishes(self):
        budget = RunBudget(
            320,
            auto_continue=True,
            continue_count=0,
            max_continue_runs=20,
            clock=lambda: 0,
            start_time=0,
        )

        status = budget.build_status(
            total_count=3,
            attempted_count=3,
            stopped_for_budget=False,
        )

        self.assertFalse(status.continue_needed)
        self.assertEqual(status.remaining_count, 0)

    def test_continuation_when_budget_stops_with_remaining_work(self):
        now = 61.0
        budget = RunBudget(
            1,
            auto_continue=True,
            continue_count=2,
            max_continue_runs=20,
            clock=lambda: now,
            start_time=0,
        )

        self.assertTrue(budget.exhausted())
        status = budget.build_status(
            total_count=5,
            attempted_count=2,
            stopped_for_budget=True,
        )

        self.assertTrue(status.continue_needed)
        self.assertEqual(status.remaining_count, 3)
        self.assertEqual(status.next_continue_count, 3)

    def test_auto_continue_false_disables_continuation(self):
        budget = RunBudget(
            1,
            auto_continue=False,
            continue_count=0,
            max_continue_runs=20,
            clock=lambda: 61.0,
            start_time=0,
        )

        status = budget.build_status(
            total_count=2,
            attempted_count=1,
            stopped_for_budget=True,
        )

        self.assertFalse(status.continue_needed)
        self.assertFalse(status.continue_blocked)

    def test_max_continue_runs_blocks_loop(self):
        budget = RunBudget(
            1,
            auto_continue=True,
            continue_count=20,
            max_continue_runs=20,
            clock=lambda: 61.0,
            start_time=0,
        )

        status = budget.build_status(
            total_count=4,
            attempted_count=1,
            stopped_for_budget=True,
        )

        self.assertFalse(status.continue_needed)
        self.assertTrue(status.continue_blocked)


if __name__ == "__main__":
    unittest.main()
