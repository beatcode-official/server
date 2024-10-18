import json
import random


class ChallengeManager:
    def __init__(self, json_path: str):
        """
        Initializes the ChallengeManager with the challenges database from the given JSON file.

        Args:
            json_path (str): The path to the JSON file containing the challenges database.
        """
        self.db_obj = json.load(open(json_path, "r"))["CHALLENGES"]

    def get_challenge(self, challenge_id: int):
        """
        Returns the challenge with the given ID.

        Args:
            challenge_id (int): The ID of the challenge to retrieve.

        Returns:
            dict: The challenge object.
        """
        return self.db_obj[challenge_id]

    def get_random_indexes(self, count: int):
        """
        Returns a list of random challenge indexes from the database.

        Args:
            count (int): The number of random challenge indexes to return.

        Returns:    
            list: A list of random challenge indexes.
        """
        return random.sample(range(len(self.db_obj)), count)
