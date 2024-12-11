import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# fmt: off
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from core.config import settings
from db.models.problem import Problem
from services.problem.service import ProblemManager
# fmt: on

sync_db_url = settings.DATABASE_URL
engine = create_engine(sync_db_url)
SessionLocal = sessionmaker(bind=engine)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.mark.asyncio
async def test_get_random_problems(db: Session):
    result1 = await ProblemManager.get_random_problems(db, "easy", 1)

    assert isinstance(result1, list)
    assert len(result1) > 0
    assert all(prob.difficulty == "easy" for prob in result1)
    assert len(result1) <= 1

    result2 = await ProblemManager.get_random_problems(db, "easy", 1)
    result3 = await ProblemManager.get_random_problems(db, "easy", 1)
    result4 = await ProblemManager.get_random_problems(db, "easy", 1)
    result5 = await ProblemManager.get_random_problems(db, "easy", 1)
    result = [result1, result2, result3, result4, result5]

    # Since it's random, the chance of all 5 results being the same is very low
    # Test if the length of the set of problem ids is greater than 1
    assert len(set([res[0].id for res in result])) > 1


@pytest.mark.asyncio
async def test_get_problem_by_id(db: Session):
    problem = db.query(Problem).first()

    assert problem
    result = await ProblemManager.get_problem_by_id(db, problem.id)

    assert result
    assert problem.id == result.id
    assert problem.title == result.title
    assert problem.description == result.description
    assert problem.difficulty == result.difficulty
    assert problem.sample_test_cases == result.sample_test_cases
    assert problem.sample_test_results == result.sample_test_results
    assert problem.boilerplate == result.boilerplate


@pytest.mark.asyncio
async def test_get_problems_by_distribution(db: Session):
    distribution = {"easy": 1, "medium": 1}

    result = await ProblemManager.get_problems_by_distribution(db, distribution)

    assert isinstance(result, list)
    assert len(result) > 0
    difficulties = [prob.difficulty for prob in result]
    assert all(diff in ["easy", "medium"] for diff in difficulties)
    assert len(result) <= sum(distribution.values())


def test_prepare_problem_for_client(db: Session):
    problem = db.query(Problem).first()

    assert problem
    result = ProblemManager.prepare_problem_for_client(problem)

    assert "title" in result
    assert "description" in result
    assert "difficulty" in result
    assert "sample_test_cases" in result
    assert "sample_test_results" in result
    assert "boilerplate" in result
    assert "hidden_test_cases" not in result
    assert "hidden_test_results" not in result
    assert "compare_func" not in result


def test_get_problem_for_validation(db: Session):
    problem = db.query(Problem).first()

    assert problem
    result = ProblemManager.get_problem_for_validation(problem)

    assert "hidden_test_cases" in result
    assert "hidden_test_results" in result
    assert "sample_test_cases" in result
    assert "sample_test_results" in result
    assert "compare_func" in result
    assert "title" not in result
    assert "description" not in result


@pytest.mark.asyncio
async def test_get_random_problems_empty_result(db: Session):
    result = await ProblemManager.get_random_problems(db, "nonexistent_difficulty", 1)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_problems_by_distribution_empty_distribution(db: Session):
    distribution = {}
    result = await ProblemManager.get_problems_by_distribution(db, distribution)
    assert len(result) == 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
