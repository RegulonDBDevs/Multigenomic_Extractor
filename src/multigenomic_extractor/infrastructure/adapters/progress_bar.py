class ProgressBar:
    def __init__(self, total: int, width: int = 40):
        self.total = max(total, 1)
        self.width = width
        self.current = 0

    def update(self, step: int = 1):
        self.current += step
        ratio = min(self.current / self.total, 1)
        filled = int(self.width * ratio)

        bar = "█" * filled + "-" * (self.width - filled)
        percent = ratio * 100

        print(
            f"\r[{bar}] {self.current}/{self.total} ({percent:.2f}%)",
            end="",
            flush=True,
        )

    def finish(self):
        print()
