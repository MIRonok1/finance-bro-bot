from app.srs import DEFAULT_EASINESS_FACTOR, MIN_EASINESS_FACTOR, sm2_update


def test_sm2_correct_sequence_grows_interval_and_easiness_factor():
    """При quality=5 ('верно') каждая успешная попытка добавляет +0.1 к EF и
    растит интервал по стандартной формуле SM-2: 1, 6, 16, 45 дней."""
    ef, interval, reps = DEFAULT_EASINESS_FACTOR, 0, 0

    ef, interval, reps = sm2_update(ef, interval, reps, is_correct=True)
    assert (interval, reps) == (1, 1)
    assert round(ef, 4) == 2.6

    ef, interval, reps = sm2_update(ef, interval, reps, is_correct=True)
    assert (interval, reps) == (6, 2)
    assert round(ef, 4) == 2.7

    ef, interval, reps = sm2_update(ef, interval, reps, is_correct=True)
    assert (interval, reps) == (16, 3)
    assert round(ef, 4) == 2.8

    ef, interval, reps = sm2_update(ef, interval, reps, is_correct=True)
    assert (interval, reps) == (45, 4)
    assert round(ef, 4) == 2.9


def test_sm2_incorrect_resets_repetitions_and_interval():
    ef, interval, reps = sm2_update(2.5, 15, 3, is_correct=False)
    assert reps == 0
    assert interval == 1


def test_sm2_incorrect_lowers_easiness_factor():
    ef, _, _ = sm2_update(2.5, 15, 3, is_correct=False)
    assert ef < 2.5


def test_sm2_correct_raises_easiness_factor():
    ef, _, _ = sm2_update(2.5, 1, 0, is_correct=True)
    assert ef > 2.5


def test_sm2_easiness_factor_never_drops_below_floor():
    ef = 1.3
    for _ in range(10):
        ef, _, _ = sm2_update(ef, 1, 0, is_correct=False)
    assert ef == MIN_EASINESS_FACTOR


def test_sm2_first_correct_review_sets_interval_to_one_day():
    _, interval, reps = sm2_update(DEFAULT_EASINESS_FACTOR, 0, 0, is_correct=True)
    assert interval == 1
    assert reps == 1


def test_sm2_second_correct_review_sets_interval_to_six_days():
    _, interval, reps = sm2_update(DEFAULT_EASINESS_FACTOR, 1, 1, is_correct=True)
    assert interval == 6
    assert reps == 2


def test_sm2_repeated_failures_keep_interval_at_one_day():
    ef, interval, reps = DEFAULT_EASINESS_FACTOR, 15, 3
    for _ in range(3):
        ef, interval, reps = sm2_update(ef, interval, reps, is_correct=False)
        assert interval == 1
        assert reps == 0
