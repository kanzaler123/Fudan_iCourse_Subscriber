"""Run-budget and auto-continuation helpers for GitHub Actions."""

from __future__ import annotations

from dataclasses import dataclass
import os
import time
from typing import Callable


@dataclass(frozen=True)
class ContinuationStatus:
    total_count: int
    attempted_count: int
    remaining_count: int
    stopped_for_budget: bool
    auto_continue: bool
    continue_count: int
    max_continue_runs: int
    continue_needed: bool
    continue_blocked: bool

    @property
    def next_continue_count(self) -> int:
        return self.continue_count + 1


class RunBudget:
    """Tracks the soft time limit for one workflow run."""

    def __init__(
        self,
        max_run_minutes: int,
        *,
        auto_continue: bool,
        continue_count: int,
        max_continue_runs: int,
        clock: Callable[[], float] | None = None,
        start_time: float | None = None,
    ):
        self.max_run_minutes = max_run_minutes
        self.auto_continue = auto_continue
        self.continue_count = max(0, continue_count)
        self.max_continue_runs = max(0, max_continue_runs)
        self._clock = clock or time.monotonic
        self._start_time = self._clock() if start_time is None else start_time

    @classmethod
    def from_config(cls, config_module) -> "RunBudget":
        return cls(
            config_module.MAX_RUN_MINUTES,
            auto_continue=config_module.AUTO_CONTINUE,
            continue_count=config_module.CONTINUE_COUNT,
            max_continue_runs=config_module.MAX_CONTINUE_RUNS,
        )

    @property
    def enabled(self) -> bool:
        return self.max_run_minutes > 0

    def elapsed_seconds(self) -> float:
        return max(0.0, self._clock() - self._start_time)

    def exhausted(self) -> bool:
        if not self.enabled:
            return False
        return self.elapsed_seconds() >= self.max_run_minutes * 60

    def build_status(
        self,
        *,
        total_count: int,
        attempted_count: int,
        stopped_for_budget: bool,
    ) -> ContinuationStatus:
        remaining = max(0, total_count - attempted_count)
        blocked = (
            stopped_for_budget
            and remaining > 0
            and self.auto_continue
            and self.continue_count >= self.max_continue_runs
        )
        needed = (
            stopped_for_budget
            and remaining > 0
            and self.auto_continue
            and not blocked
        )
        return ContinuationStatus(
            total_count=total_count,
            attempted_count=attempted_count,
            remaining_count=remaining,
            stopped_for_budget=stopped_for_budget,
            auto_continue=self.auto_continue,
            continue_count=self.continue_count,
            max_continue_runs=self.max_continue_runs,
            continue_needed=needed,
            continue_blocked=blocked,
        )


def write_github_outputs(
    status: ContinuationStatus,
    *,
    course_ids: list[str],
) -> None:
    """Expose continuation status to later workflow steps."""

    values = {
        "continue_needed": _bool(status.continue_needed),
        "continue_blocked": _bool(status.continue_blocked),
        "stopped_for_budget": _bool(status.stopped_for_budget),
        "remaining_count": str(status.remaining_count),
        "attempted_count": str(status.attempted_count),
        "total_count": str(status.total_count),
        "continue_count": str(status.continue_count),
        "next_continue_count": str(status.next_continue_count),
        "course_ids": ",".join(course_ids),
    }

    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as fh:
            for key, value in values.items():
                fh.write(f"{key}={value}\n")

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as fh:
            fh.write("\n### iCourse continuation\n")
            fh.write(f"- Attempted lectures: {status.attempted_count}\n")
            fh.write(f"- Remaining lectures: {status.remaining_count}\n")
            fh.write(f"- Stopped for budget: {_bool(status.stopped_for_budget)}\n")
            fh.write(f"- Auto-continue requested: {_bool(status.continue_needed)}\n")
            if status.continue_blocked:
                fh.write("- Auto-continue blocked: max continuation count reached\n")


def _bool(value: bool) -> str:
    return "true" if value else "false"
