import pytest
from core.config import settings
from db.models import Problem
from services.problem import ProblemService
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

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
    result = await ProblemService.get_random_problems(db, "easy", 1)

    assert isinstance(result, list)
    assert len(result) > 0
    assert all(prob.difficulty == "easy" for prob in result)
    assert len(result) <= 1


@pytest.mark.asyncio
async def test_get_problems_by_distribution(db: Session):
    distribution = {"easy": 1, "medium": 1}

    result = await ProblemService.get_problems_by_distribution(db, distribution)

    assert isinstance(result, list)
    assert len(result) > 0
    difficulties = [prob.difficulty for prob in result]
    assert all(diff in ["easy", "medium"] for diff in difficulties)
    assert len(result) <= sum(distribution.values())


def test_prepare_problem_for_client(db: Session):
    problem = db.query(Problem).first()

    assert problem
    result = ProblemService.prepare_problem_for_client(problem)

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
    result = ProblemService.get_problem_for_validation(problem)

    assert "hidden_test_cases" in result
    assert "hidden_test_results" in result
    assert "compare_func" in result
    assert "title" not in result
    assert "description" not in result
    assert "sample_test_cases" not in result


@pytest.mark.asyncio
async def test_get_random_problems_empty_result(db: Session):
    result = await ProblemService.get_random_problems(db, "nonexistent_difficulty", 1)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_problems_by_distribution_empty_distribution(db: Session):
    distribution = {}
    result = await ProblemService.get_problems_by_distribution(db, distribution)
    assert len(result) == 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
