from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from threading import Lock
from time import perf_counter


@dataclass(slots=True)
class MetricsRegistry:
    _lock: Lock = field(default_factory=Lock)
    _requests_total: Counter[tuple[str, str, int]] = field(default_factory=Counter)
    _errors_total: Counter[tuple[str, str, int]] = field(default_factory=Counter)
    _duration_sum: defaultdict[tuple[str, str], float] = field(
        default_factory=lambda: defaultdict(float)
    )
    _duration_count: Counter[tuple[str, str]] = field(default_factory=Counter)

    def observe(self, *, method: str, path: str, status_code: int, duration_seconds: float) -> None:
        key = (method, path, status_code)
        duration_key = (method, path)
        with self._lock:
            self._requests_total[key] += 1
            self._duration_sum[duration_key] += duration_seconds
            self._duration_count[duration_key] += 1
            if status_code >= 400:
                self._errors_total[key] += 1

    def render_prometheus(self) -> str:
        lines = [
            "# HELP splitmint_http_requests_total Total HTTP requests handled.",
            "# TYPE splitmint_http_requests_total counter",
        ]
        with self._lock:
            for (method, path, status), value in sorted(self._requests_total.items()):
                lines.append(
                    "splitmint_http_requests_total"
                    f'{{method="{method}",path="{path}",status="{status}"}} {value}'
                )

            lines.extend(
                [
                    "# HELP splitmint_http_errors_total Total HTTP responses with status >= 400.",
                    "# TYPE splitmint_http_errors_total counter",
                ]
            )
            for (method, path, status), value in sorted(self._errors_total.items()):
                lines.append(
                    "splitmint_http_errors_total"
                    f'{{method="{method}",path="{path}",status="{status}"}} {value}'
                )

            lines.extend(
                [
                    "# HELP splitmint_http_request_duration_seconds_sum Cumulative HTTP request duration.",
                    "# TYPE splitmint_http_request_duration_seconds_sum counter",
                ]
            )
            for (method, path), value in sorted(self._duration_sum.items()):
                lines.append(
                    "splitmint_http_request_duration_seconds_sum"
                    f'{{method="{method}",path="{path}"}} {value:.6f}'
                )

            lines.extend(
                [
                    "# HELP splitmint_http_request_duration_seconds_count Number of timed HTTP requests.",
                    "# TYPE splitmint_http_request_duration_seconds_count counter",
                ]
            )
            for (method, path), value in sorted(self._duration_count.items()):
                lines.append(
                    "splitmint_http_request_duration_seconds_count"
                    f'{{method="{method}",path="{path}"}} {value}'
                )
        return "\n".join(lines) + "\n"

    def timer(self) -> float:
        return perf_counter()


metrics_registry = MetricsRegistry()
