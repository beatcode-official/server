from typing import Dict, List

from db.models import Problem
from sqlalchemy import func
from sqlalchemy.orm import Session


class ProblemService:
    @staticmethod
    async def get_random_problems(
        db: Session,
        difficulty: str,
        count: int
    ) -> List[Problem]:
        return (
            db.query(Problem)
            .filter(Problem.difficulty == difficulty)
            .order_by(func.random())
            .limit(count)
            .all()
        )

    @staticmethod
    async def get_problems_by_distribution(
        db: Session,
        distribution: Dict[str, int]
    ) -> List[Problem]:
        problems = []

        for difficulty, count in distribution.items():
            difficulty_problems = await ProblemService.get_random_problems(
                db, difficulty, count
            )
            problems.extend(difficulty_problems)

        return problems

    @staticmethod
    def prepare_problem_for_client(problem: Problem) -> Dict:
        return {
            "title": problem.title,
            "description": problem.description,
            "difficulty": problem.difficulty,
            "sample_test_cases": problem.sample_test_cases,
            "sample_test_results": problem.sample_test_results,
            "boilerplate": problem.boilerplate,
        }

    @staticmethod
    def get_problem_for_validation(problem: Problem) -> Dict:
        return {
            "hidden_test_cases": problem.hidden_test_cases,
            "hidden_test_results": problem.hidden_test_results,
            "compare_func": problem.compare_func,
        }
