import random
from typing import Dict, List
from sqlalchemy import func
from sqlalchemy.orm import Session
from db.models import DifficultyLevel, Problem


class ProblemService:
    @staticmethod
    async def get_random_problems(
        db: Session,
        difficulty: DifficultyLevel,
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
        distribution: Dict[DifficultyLevel, int]
    ) -> List[Problem]:
        problems = []

        for difficulty, count in distribution.items():
            difficulty_problems = await ProblemService.get_random_problems(
                db, difficulty, count
            )
            problems.extend(difficulty_problems)

        random.shuffle(problems)
        return problems

    @staticmethod
    def prepare_problem_for_client(problem: Problem) -> Dict:
        return {
            "id": problem.id,
            "title": problem.title,
            "description": problem.description,
            "difficulty": problem.difficulty,
            "time_limit_ms": problem.time_limit_ms,
            "memory_limit_mb": problem.memory_limit_mb,
            "sample_test_cases": problem.sample_test_cases,
            "sample_test_results": problem.sample_test_results,
            "boilerplate": problem.boilerplate,
        }

    @staticmethod
    def get_problem_for_validation(problem: Problem) -> Dict:
        return {
            "id": problem.id,
            "hidden_test_cases": problem.hidden_test_cases,
            "hidden_test_results": problem.hidden_test_results,
            "compare_func": problem.compare_func,
            "time_limit_ms": problem.time_limit_ms,
            "memory_limit_mb": problem.memory_limit_mb,
        }
