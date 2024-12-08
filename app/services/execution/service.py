import asyncio
import os
import tempfile
from typing import List

import docker
from core.config import settings
from services.execution.docker import DockerRunner
from services.execution.test_generator import TestGenerator
from services.execution.types import ExecutionResult
from services.execution.runtime_analysis import runtime_analysis_service


class CodeExecutionService:
    """
    A service class in charge of executing code.
    """

    def __init__(self):
        self.docker = DockerRunner(docker.from_env())
        self.test_generator = TestGenerator()
        easy, medium, hard = [
            int(x) for x in settings.MAX_CONCURRENT.split(",")
        ]
        self._execution_semaphores = {
            "easy": asyncio.Semaphore(easy),
            "medium": asyncio.Semaphore(medium),
            "hard": asyncio.Semaphore(hard),
        }

    async def execute_code(
        self,
        code: str,
        test_cases: List[str],
        expected_results: List[str],
        difficulty: str,
        compare_func: str,
    ) -> ExecutionResult:
        """
        Execute the code with the given test cases and expected results.

        :param code: The code to execute.
        :param test_cases: A list of test cases.
        :param expected_results: A list of expected results.
        :param difficulty: The difficulty of the problem.
        :param compare_func: The name of the comparison function.
        """
        # Limit the number of concurrent executions based on the difficulty level.
        sem = self._execution_semaphores[difficulty.lower()]

        async with sem:  # blocks until a semaphore is available

            # Create a temporary file to store the test runner file.
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                # Test data are pairs of test cases and its expected results.
                test_data = [
                    {"input": tc, "expected": er}
                    for tc, er in zip(test_cases, expected_results)
                ]
                f.write(self.test_generator.generate_test_runner(code, test_data, compare_func))
                file_path = f.name

            try:
                result = self.docker.run_container(file_path, difficulty)

                # If all tests passed, get runtime analysis
                if result.all_cleared():
                    runtime_analysis = await runtime_analysis_service.analyze_code(code)
                    result.runtime_analysis = runtime_analysis

                return result
            finally:
                # Clean up the temporary file
                os.unlink(file_path)


code_execution = CodeExecutionService()
