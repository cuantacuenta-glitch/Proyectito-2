from dataclasses import dataclass, field, asdict
from pathlib import Path
import json

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
DATA.mkdir(exist_ok=True)
CFG_PATH = DATA / "config.json"
LAYOUT_PATH = DATA / "layout.json"

TITLE_RE = r"(?i)hold'?em|omaha|stud|draw"


@dataclass
class Config:
    # --- cliente ---
    client_process: list[str] = field(default_factory=lambda: ["PokerClient.exe"])
    window_classes: list[str] = field(default_factory=list)
    title_regex: str = TITLE_RE
    min_table_size: tuple[int, int] = (300, 220)

    table_seats: int = 6
    hero_seat: int = 0

    # --- captura ---
    target_fps: int = 10
    capture_backend: str = "dxcam"        # dxcam | mss

    # --- lectura ---
    ocr_min_conf: float = 0.45

    # --- depuracion ---
    debug_grid: bool = True
    debug_fps: bool = True

    def __post_init__(self):
        self.min_table_size = tuple(self.min_table_size)

    def save(self):
        CFG_PATH.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @classmethod
    def load(cls):
        if CFG_PATH.exists():
            try:
                return cls(**json.loads(CFG_PATH.read_text(encoding="utf-8")))
            except Exception:
                pass
        c = cls()
        c.save()
        return c