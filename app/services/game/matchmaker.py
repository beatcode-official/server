import random
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from core.config import settings
from db.models.user import User
from fastapi import WebSocket
from services.game.ranked import RankedService


class Matchmaker:
    """
    A class representing the matchmaker service.
    """

    def __init__(self):
        self.unranked_queue: Set[Tuple[WebSocket, User]] = set()
        self.ranked_queue: List[Tuple[float, WebSocket, User]] = []

        self.match_problem_count = settings.MATCH_PROBLEM_COUNT
        self.prob_easy, self.prob_medium, self.prob_hard = [
            float(x) for x in settings.UNRANKED_PROBS.split(",")
        ]
        self.ranked_service = RankedService()

    async def add_to_queue(
        self, ws: WebSocket, user: User, ranked: bool = False
    ) -> bool:
        """
        Adds a player to the queue if they are not already in it.

        :param ws: The WebSocket connection of the player.
        :param user: The user to add to the queue.
        :param ranked: Whether to add to ranked or unranked queue
        :return: True if the user was added to the queue, False otherwise.
        """
        if any(user.id == u.id for _, u in self.unranked_queue) or any(
            user.id == u.id for _, _, u in self.ranked_queue
        ):
            return False

        if ranked:
            self.ranked_queue.append((user.rating, ws, user))
            # Sort queue by rating for easier matchmaking
            self.ranked_queue.sort(key=lambda x: x[0])
        else:
            self.unranked_queue.add((ws, user))
        return True

    async def remove_from_queue(self, user_id: int):
        """
        Removes a player from both queues.

        :param user_id: The ID of the user to remove from the queue.
        """
        self.unranked_queue = {
            (ws, user) for ws, user in self.unranked_queue if user.id != user_id
        }

        self.ranked_queue = [
            (rating, ws, user)
            for rating, ws, user in self.ranked_queue
            if user.id != user_id
        ]

    async def get_ranked_match(self) -> Optional[List[Tuple[WebSocket, User]]]:
        """
        Try to find a ranked match based on rating proximity.

        :return: A list of players if a match was found, None otherwise.
        """
        if len(self.ranked_queue) < 2:
            return None

        # Find the closest pair of ratings
        min_diff = float("inf")
        best_pair_idx = None

        # Compare adjacent pairs in the sorted queue
        for i in range(len(self.ranked_queue) - 1):
            diff = abs(self.ranked_queue[i][0] - self.ranked_queue[i + 1][0])
            if diff < min_diff:
                min_diff = diff
                best_pair_idx = i

        if best_pair_idx is not None:
            # Get the pair and remove them from queue
            _, ws1, user1 = self.ranked_queue.pop(best_pair_idx)
            _, ws2, user2 = self.ranked_queue.pop(best_pair_idx)
            return [(ws1, user1), (ws2, user2)]

        return None

    async def get_random_player(self, count: int = 2) -> List[Tuple[WebSocket, User]]:
        """
        Gets 2 random players from the unranked queue.

        :return: A list of players.
        """
        if len(self.unranked_queue) < count:
            return []

        selected_players = random.sample(list(self.unranked_queue), count)

        # Remove selected players from the queue
        for player in selected_players:
            self.unranked_queue.remove(player)

        return selected_players

    def get_problem_distribution(
        self, ranked: bool = False, rating: float = 0
    ) -> Dict[str, int]:
        """
        Get the problem distribution based on queue type and rating.

        :param ranked: Whether this is for a ranked match
        :param rating: Player's rating (for ranked matches)
        :return: Dictionary mapping difficulty to number of problems
        """
        if settings.TESTING:
            if ranked:
                return {"easy": 0, "medium": 0, "hard": 3}
            return {"easy": 3, "medium": 0, "hard": 0}

        if ranked:
            return self.ranked_service.get_problem_distribution(rating)

        # For unranked, convert probability to fixed count
        distribution = defaultdict(int)
        for _ in range(self.match_problem_count):
            r = random.random()
            if r < self.prob_easy:
                distribution["easy"] += 1
            elif r < self.prob_easy + self.prob_medium:
                distribution["medium"] += 1
            else:
                distribution["hard"] += 1

        return dict(distribution)
