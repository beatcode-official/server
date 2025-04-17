import os
import sys

from openai import AsyncOpenAI
from pydantic import BaseModel, Field
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from core.config import settings
from db.models.problem import Problem
from services.execution.service import CodeExecutionService

sync_db_url = settings.DATABASE_URL
engine = create_engine(sync_db_url)
SessionLocal = sessionmaker(bind=engine)


class CodeGenerationResponse(BaseModel):
    python: str = Field(..., description="Solution in Python")
    java: str = Field(..., description="Solution in Java")
    cpp: str = Field(..., description="Solution in C++")


class CodeGenerationService:
    def __init__(self, api_key: str):
        self.client = (
            AsyncOpenAI(api_key=api_key) if api_key != "your_api_key_here" else None
        )

    async def generate_code(
        self, title: str, description: str, boilerplate: str
    ) -> CodeGenerationResponse:
        if not self.client:
            return CodeGenerationResponse()
        try:
            completion = await self.client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a code generation assistant. Generate correct solutions in python, java, and c++.",
                    },
                    {
                        "role": "user",
                        "content": f"Title: {title}\nProblem description:\n{description}\nBoilerplates:\n{boilerplate.python}\n{boilerplate.java}\n{boilerplate.cpp}\nReturn only JSON with python, java, and cpp fields.",
                    },
                ],
                response_format=CodeGenerationResponse,
                temperature=0,
            )
            return completion.choices[0].message.parsed
        except Exception:
            return CodeGenerationResponse()


def get_compare_func(problem: Problem, lang: str) -> str:
    if lang == "python":
        return problem.compare_func.python
    elif lang == "java":
        return problem.compare_func.java
    elif lang == "cpp":
        return problem.compare_func.cpp


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.mark.asyncio
async def test_code_validation_all_problems(db: Session):
    print("Setting up...")
    code_generator = CodeGenerationService(settings.OPENAI_API_KEY)
    executor = CodeExecutionService()
    problems = db.query(Problem).all()
    print(f"Validating {len(problems)} problems")
    for problem in problems:
        print(f"Validating problem: {problem.title}")
        code_res = await code_generator.generate_code(
            problem.title, problem.description, problem.boilerplate
        )
        for lang, snippet in [
            ("python", code_res.python),
            ("java", code_res.java),
            ("cpp", code_res.cpp),
        ]:
            print(f"Validating {lang} code")
            if snippet.strip():
                result = await executor.execute_code(
                    code=snippet,
                    lang=lang,
                    method_name=problem.method_name,
                    test_cases=problem.hidden_test_cases,
                    expected_results=problem.hidden_test_results,
                    sample_test_cases=problem.sample_test_cases,
                    sample_expected_results=problem.sample_test_results,
                    difficulty=problem.difficulty,
                    compare_func=get_compare_func(problem, lang),
                )
                if not result.success:
                    print(snippet)
                print(result.message)
                assert result.success
                all_passed = True
                for tr in result.test_results:
                    if "error" in tr:
                        print(tr)
                    if not tr["passed"]:
                        all_passed = False
                    assert "error" not in tr or not tr["error"]
                print(
                    f"{lang} code validation successful: {'all passed' if all_passed else 'a few failed'}"
                )
