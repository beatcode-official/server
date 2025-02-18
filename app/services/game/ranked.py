from typing import Dict

from core.config import settings


class RankedService:
    """
    A service class for handling ranked-specific logic
    """

    def __init__(self):
        thresholds = [int(x) for x in settings.RANK_THRESHOLDS.split(",")]
        names = [x.strip() for x in settings.RANK_NAMES.split(",")]
        self.k_factor = settings.RATING_K_FACTOR

        # Map thresholds to rank names
        self.rank_thresholds = dict(zip(thresholds, names))

        # Parse problem distribution for each rank
        distributions = settings.RANK_PROBLEM_DISTRIBUTION.split(",")
        self.rank_problems: Dict[str, Dict[str, int]] = {}

        for rank, dist in zip(names, distributions):
            easy, medium, hard = [int(x) for x in dist.split("-")]
            self.rank_problems[rank] = {"easy": easy, "medium": medium, "hard": hard}

    def get_rank(self, rating: float) -> str:
        """
        Get the rank name for a given rating

        :param rating: Player's rating
        :return: Rank name
        """
        for threshold, rank_name in sorted(self.rank_thresholds.items()):
            if rating >= threshold:
                current_rank = rank_name
            else:
                break
        return current_rank

    def get_problem_distribution(self, rating: float) -> Dict[str, int]:
        """
        Get the problem distribution for a given rating

        :param rating: Player's rating
        :return: Dictionary mapping problem difficulty to number of problems
        """
        rank = self.get_rank(rating)
        return self.rank_problems[rank]

    def calculate_rating_change(
        self, player_rating: float, opponent_rating: float, won: bool
    ) -> float:
        """
        Calculate rating change using ELO-like system

        :param player_rating: Rating of the player
        :param opponent_rating: Rating of the opponent
        :param won: Whether the player won
        :return: Rating change (positive for gain, negative for loss)
        """
        # Calculate expected score using logistic curve
        expected_score = 1 / (1 + 10 ** ((opponent_rating - player_rating) / 400))

        # Actual score is 1 for win, 0 for loss
        actual_score = 1 if won else 0

        # Calculate rating change
        rating_change = self.k_factor * (actual_score - expected_score)

        return round(rating_change, 1)
