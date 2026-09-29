from time import perf_counter


class Timer:
    def __enter__(self) -> "Timer":
        self._started = perf_counter()
        self.elapsed_ms = 0
        return self

    def __exit__(self, *_: object) -> None:
        self.elapsed_ms = round((perf_counter() - self._started) * 1000)
