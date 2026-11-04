"""Terminal progress bars that can coexist without overwriting one another."""
import sys


class ProgressBar:
    _active = []
    _rendered_lines = 0

    def __init__(self, total: int, width: int = 40, label: str = "Progreso"):
        self.total = max(total, 1)
        self.width = width
        self.current = 0
        self.label = label
        self._finished = False
        ProgressBar._active.append(self)
        self._render()

    def update(self, step: int = 1):
        self.current = min(self.total, self.current + step)
        self._render()

    def _line(self):
        ratio = min(self.current / self.total, 1)
        filled = int(self.width * ratio)
        bar = "█" * filled + "-" * (self.width - filled)
        return f"{self.label}: [{bar}] {self.current}/{self.total} ({ratio * 100:.2f}%)"

    @classmethod
    def _render(cls):
        if not cls._active:
            return
        if sys.stdout.isatty():
            if cls._rendered_lines:
                sys.stdout.write(f"\x1b[{cls._rendered_lines}A")
            for bar in cls._active:
                sys.stdout.write("\x1b[2K" + bar._line() + "\n")
            # Clear rows left over when a second bar disappears.
            for _ in range(max(0, cls._rendered_lines - len(cls._active))):
                sys.stdout.write("\x1b[2K\n")
            cls._rendered_lines = max(cls._rendered_lines, len(cls._active))
            sys.stdout.flush()
        else:
            # Logs and redirected output: avoid ANSI escape codes.
            for bar in cls._active:
                print(bar._line(), flush=True)

    def finish(self):
        if self._finished:
            return
        self._finished = True
        if self in ProgressBar._active:
            ProgressBar._active.remove(self)
        if sys.stdout.isatty():
            # Preserve the completed bar as a normal terminal line, then
            # redraw the still-active bars below it.
            if ProgressBar._rendered_lines:
                sys.stdout.write(f"\x1b[{ProgressBar._rendered_lines}A")
            sys.stdout.write("\x1b[2K" + self._line() + "\n")
            for bar in ProgressBar._active:
                sys.stdout.write("\x1b[2K" + bar._line() + "\n")
            for _ in range(max(0, ProgressBar._rendered_lines - len(ProgressBar._active) - 1)):
                sys.stdout.write("\x1b[2K\n")
            sys.stdout.flush()
            ProgressBar._rendered_lines = len(ProgressBar._active)
        else:
            print(self._line(), flush=True)
