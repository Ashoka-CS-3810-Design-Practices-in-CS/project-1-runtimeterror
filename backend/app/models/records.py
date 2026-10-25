#storing the records of the Data layer Event, Task and Preferences.

from dataclasses import dataclass, field

CATEGORIES = ("meeting", "class", "appointment", "assignment", "personal")
PRIORITIES = ("High", "Medium", "Low")          
TIMES_OF_DAY = ("morning", "afternoon", "night")
CUTOFF_MODES = ("Flexible", "Strict")

DEFAULT_MOVABLE = {
    "meeting": False,
    "class": False,
    "appointment": False,
    "assignment": True,
    "personal": True,
}

MIN_DURATION = 5           
MAX_DURATION = 24 * 60     


@dataclass(frozen=True)
class Event:
    id: int | None
    title: str
    start: int                 
    end: int                   
    category: str
    description: str = ""
    location: str = ""
    priority: str | None = None
    movable: bool | None = None

    def __post_init__(self):
        if self.movable is None:
            object.__setattr__(self, "movable", DEFAULT_MOVABLE[self.category])

    @property
    def duration(self) -> int:
        return self.end - self.start
#task has no start end once accepted the time suggested we can make it event with times

@dataclass(frozen=True)
class Task:
    id: int | None
    name: str
    category: str
    duration: int              
    priority: str              
    from_date: str | None = None     
    to_date: str | None = None       
    daily_start: int | None = None   
    daily_end: int | None = None

#adding for explaoner
PRIORITY_RULES = ("earliest_start", "best_fit")


@dataclass(frozen=True)
class Slot:
    start: int
    end: int
    gap_start: int
    gap_end: int
    gap_length: int
    leftover: int
    before_cutoff: bool
    matches_preferred: bool
    priority_rule: str                  # "earliest_start" or "best_fit"
    reasons: tuple[str, ...] = ()       # filled in by the Explainer


@dataclass
class Preferences:
    preferred_time: dict = field(default_factory=lambda: {
        "meeting": "morning",
        "class": "morning",
        "appointment": "afternoon",
        "assignment": "morning",
        "personal": "night",
    })
    cutoff: int = 21 * 60              
    cutoff_mode: str = "Flexible"      
    working_start: int = 9 * 60        
    working_end: int = 18 * 60        