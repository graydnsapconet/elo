import math

# Constants
FORM_CONST = 0.1

def calculate_expectation(elo_a, elo_b):
    expected_a = 1 / (1 + 10 ** ((elo_b - elo_a) / 400))
    return expected_a, 1 - expected_a

def calculate_base_k(games_played):
    if games_played < 3:
        return 35
    elif games_played <= 5:
        return 30
    elif games_played <= 10:
        return 25
    elif games_played <= 20:
        return 20
    return max(15, 50 / math.sqrt(games_played + 1))

def adjust_k_for_streak(base_k, streak):
    adjustment = -FORM_CONST * streak if streak > 0 else FORM_CONST * abs(streak)
    return min(25, base_k * (1 + adjustment))

def underdog_adjustment(elo_a, elo_b, k_a, k_b):
    rating_diff = abs(elo_a - elo_b)
    underdog_boost = min(2, rating_diff / 100)
    if elo_a < elo_b:
        k_a += underdog_boost
    else:
        k_b += underdog_boost
    return k_a, k_b

def update_ratings(elo_a, elo_b, expected_a, expected_b, outcome, k_a, k_b):
    actual_a = 0.5 if outcome == 2 else (1 if outcome == 0 else 0)
    actual_b = 0.5 if outcome == 2 else (1 if outcome == 1 else 0)
    return (elo_a + k_a * (actual_a - expected_a), 
            elo_b + k_b * (actual_b - expected_b))

def calculate_new_ratings(elo_a, elo_b, games_played_a, games_played_b, streak_a, streak_b, outcome, multiplier=1):
    expected_a, expected_b = calculate_expectation(elo_a, elo_b)
    base_k_a, base_k_b = calculate_base_k(games_played_a), calculate_base_k(games_played_b)
    adjusted_k_a = adjust_k_for_streak(base_k_a, streak_a) * multiplier
    adjusted_k_b = adjust_k_for_streak(base_k_b, streak_b) * multiplier
    adjusted_k_a, adjusted_k_b = underdog_adjustment(elo_a, elo_b, adjusted_k_a, adjusted_k_b)
    return update_ratings(elo_a, elo_b, expected_a, expected_b, outcome, adjusted_k_a, adjusted_k_b)
