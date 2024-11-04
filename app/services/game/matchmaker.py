import random
from typing import List, Set, Tuple

from core.config import settings
from db.models.user import User
from fastapi import WebSocket


class Matchmaker:
    """
    A class representing the matchmaker service.
    """

    def __init__(self):
        self.queue: Set[Tuple[WebSocket, User]] = set()
        self.match_problem_count = settings.MATCH_PROBLEM_COUNT
        self.prob_easy = settings.PROB_EASY
        self.prob_medium = settings.PROB_MEDIUM
        self.prob_hard = settings.PROB_HARD

    async def add_to_queue(self, ws: WebSocket, user: User) -> bool:
        """
        Adds a player to the queue if they are not already in it.

        :param ws: The WebSocket connection of the player.
        :param user: The user to add to the queue.
        :return: True if the user was added to the queue, False otherwise.
        """
        if any(user.id == u.id for _, u in self.queue):
            return False

        self.queue.add((ws, user))
        return True

    async def remove_from_queue(self, user_id: int):
        """
        Removes a player from the queue.

        :param user_id: The ID of the user to remove from the queue.
        """
        self.queue = {
            (ws, user) for ws, user in self.queue if user.id != user_id
        }

    async def get_random_player(self, count: int = 2) -> List[Tuple[WebSocket, User]]:
        """
        Gets a random player from the queue.

        :param count: The number of players to get.
        :return: A list of players.
        """
        if len(self.queue) < count:
            return []

        selected_players = random.sample(list(self.queue), count)

        # Remove selected players from the queue
        for player in selected_players:
            self.queue.remove(player)

        return selected_players

    def get_problem_distribution(self) -> List[str]:
        """
        Generates a list of problems for a match based on the probabilities given
        """
        problems = []
        for _ in range(self.match_problem_count):
            r = random.random()
            if r < self.prob_easy:
                problems.append("easy")
            elif r < self.prob_easy + self.prob_medium:
                problems.append("medium")
            else:
                problems.append("hard")
        return problems
