from __future__ import annotations

from time import perf_counter


def run_empty_benchmark(iterations: int = 1000) -> dict[str, float]:
    started = perf_counter()
    for _ in range(iterations):
        pass
    elapsed = perf_counter() - started
    return {"iterations": float(iterations), "elapsed_sec": elapsed}


if __name__ == "__main__":
    print(run_empty_benchmark())
