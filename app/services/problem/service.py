import random
from typing import Dict, List, Optional

from core.config import settings
from db.models.problem import Problem
from sqlalchemy import func
from sqlalchemy.orm import Session


class ProblemManager:
    """
    A static class to handle all the operations related to fetching and preparing problems for the other services.
    """

    @staticmethod
    async def get_random_problems(
        db: Session, difficulty: str, count: int
    ) -> List[Problem]:
        """
        Get a specified number of problems of a specific difficulty level randomly.

        :param db: The database session.
        :param difficulty: The difficulty level of the problems.
        :param count: The number of problems to be fetched.

        :return: A list of problems of the specified difficulty level.
        """
        return (
            db.query(Problem)
            .filter(Problem.difficulty == difficulty)
            .order_by(func.random())
            .limit(count)
            .all()
        )

    @staticmethod
    async def get_problem_by_id(db: Session, problem_id: int) -> Optional[Problem]:
        """
        Get a problem by its ID.

        :param db: The database session.
        :param problem_id: The ID of the problem to be fetched.

        :return: The problem with the specified ID, if it exists.
        """
        return db.query(Problem).filter(Problem.id == problem_id).first()

    @staticmethod
    async def get_problems_by_distribution(
        db: Session, distribution: Dict[str, int], shuffle: bool = False
    ) -> List[Problem]:
        """
        Get problems based on the distribution of difficulty levels.

        :param db: The database session.
        :param distribution: A dictionary containing the difficulty levels and the number of problems to be fetched for each difficulty level.
        """
        problems = []

        # Feed each difficulty and count into the get_random_problems method
        for difficulty, count in distribution.items():
            difficulty_problems = await ProblemManager.get_random_problems(
                db, difficulty, count
            )
            problems.extend(difficulty_problems)

        if shuffle:
            random.shuffle(problems)

        return problems

    @staticmethod
    def prepare_problem_for_client(problem: Problem, explanation: bool = False) -> Dict:
        """
        Return a non-sensitive version of the problem that can be sent to the client.

        :param problem: The problem to be prepared.
        """
        result = {
            "title": problem.title,
            "source": problem.source,
            "description": problem.description,
            "difficulty": problem.difficulty,
            "sample_test_cases": problem.sample_test_cases,
            "sample_test_results": problem.sample_test_results,
            "boilerplate": {
                "java": problem.boilerplate.java,
                "cpp": problem.boilerplate.cpp,
                "python": problem.boilerplate.python,
            },
        }
        if explanation:
            result["explanation"] = problem.explanation
        return result

    @staticmethod
    def get_problem_for_validation(problem: Problem) -> Dict:
        """
        Return a stripped-down version of the problem that can be used for validation.
        """
        if settings.TESTING:
            return {
                "hidden_test_cases": [
                    "--arg1=true",
                    "--arg1=true",
                    "--arg1=true",
                    "--arg1=true",
                    "--arg1=true",
                    "--arg1=true",
                    "--arg1=true",
                    "--arg1=false",
                    "--arg1=false",
                    "--arg1=false",
                ],
                "hidden_test_results": [
                    "false",
                    "false",
                    "false",
                    "false",
                    "false",
                    "false",
                    "false",
                    "true",
                    "true",
                    "true",
                ],
                # "compare_func": "return str(result) == expected",
                "sample_test_cases": [
                    "--arg1=true",
                    "--arg2=false",
                ],
                "sample_test_results": [
                    "false",
                    "true",
                ],
            }

        return {
            "hidden_test_cases": problem.hidden_test_cases,
            "hidden_test_results": problem.hidden_test_results,
            "sample_test_cases": problem.sample_test_cases,
            "sample_test_results": problem.sample_test_results,
            "method_name": problem.method_name,
            "compare_func": problem.compare_func,
        }
