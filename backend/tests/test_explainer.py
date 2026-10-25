from app.algorithms.explainer import explain_slot, format_clock, format_duration
from app.algorithms.slot_ranking import rank_slots

CUTOFF = 21 * 60


def make_slot(**overrides):
    slot = {
        "start": 570, "end": 660,         
        "gap_start": 570, "gap_end": 720,   
        "gap_length": 150, "leftover": 60,
        "before_cutoff": True, "matches_preferred": True,
        "priority_rule": "earliest_start", "priority_key": 570,
    }
    slot.update(overrides)
    return slot

def explain(slot, priority="High", category="assignment", preferred="morning"):
    return explain_slot(slot, 90, priority, category, preferred, CUTOFF)

def test_format_duration():
    assert format_duration(150) == "2 hours 30 minutes"
    assert format_duration(60) == "1 hour"
    assert format_duration(45) == "45 minutes"
    assert format_duration(90) == "1 hour 30 minutes"


def test_format_clock():
    assert format_clock(21 * 60) == "9 PM"
    assert format_clock(21 * 60 + 30) == "9:30 PM"
    assert format_clock(0) == "12 AM"
    assert format_clock(12 * 60) == "12 PM"


def test_high_priority_matching_slot():
    assert explain(make_slot()) == [
        "Free for 2 hours 30 minutes, which fits your 90-minute task.",
        "Matches your morning preference for assignments.",
        "Ranked by earliest start, which suits a High priority task.",
    ]


def test_slot_outside_preferred_time():
    text = " ".join(explain(make_slot(matches_preferred=False)))
    assert "Outside your morning preference" in text
    assert "Matches" not in text


def test_no_preference_means_no_time_of_day_sentence():
    text = " ".join(explain(make_slot(matches_preferred=False), preferred=None))
    assert "preference" not in text


def test_after_cutoff_slot_gets_cutoff_sentence():
    text = " ".join(explain(make_slot(before_cutoff=False)))
    assert "after your 9 PM cutoff" in text


def test_before_cutoff_slot_never_mentions_cutoff():
    assert "cutoff" not in " ".join(explain(make_slot()))


def test_best_fit_sentences():
    slot = make_slot(priority_rule="best_fit", leftover=15)
    assert "only 15 minutes left over" in " ".join(explain(slot, priority="Medium"))
    slot = make_slot(priority_rule="best_fit", leftover=0)
    assert "perfect fit" in " ".join(explain(slot, priority="Low"))


def test_explanations_agree_with_real_ranking():
    gaps = [(9 * 60, 12 * 60), (13 * 60, 16 * 60), (21 * 60, 23 * 60)]
    ranked = rank_slots(gaps, 90, "Medium", "morning", CUTOFF, "Flexible")
    assert len(ranked) == 3
    for slot in ranked:
        text = " ".join(explain(slot, priority="Medium"))
        assert ("cutoff" in text) == (not slot["before_cutoff"])
        assert ("Matches" in text) == slot["matches_preferred"]


def test_straddling_slot_is_explained_as_ending_after_the_cutoff():
    slot = rank_slots([(20 * 60, 22 * 60)], 90, "High", None, CUTOFF, "Flexible")[0]
    text = " ".join(explain_slot(slot, 90, "High", "assignment", None, CUTOFF))
    assert "ends after your 9 PM cutoff" in text