import asyncio
import os
import tempfile
from typing import List

import docker
from core.config import settings
from services.execution.docker import DockerRunner
from services.execution.test_generator import PythonTestGenerator, JavaTestGenerator, CppTestGenerator
from services.execution.types import ExecutionResult
from services.execution.runtime_analysis import runtime_analysis_service

class CodeExecutionService:
    """
    A service class in charge of executing code.
    """

    def __init__(self):
        self.docker = DockerRunner(docker.from_env())
        self.test_generators = {
            "python": PythonTestGenerator(),
            "java": JavaTestGenerator(),
            "cpp": CppTestGenerator(),
        }
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
        method_name: str,
        test_cases: List[str],
        expected_results: List[str],
        sample_test_cases: List[str],
        sample_expected_results: List[str],
        difficulty: str,
        compare_func: str,
        lang: str = 'python'
    ) -> ExecutionResult:
        """
        Execute the code with the given test cases and expected results.

        :param code: The code to execute.
        :param test_cases: A list of test cases.
        :param expected_results: A list of expected results.
        :param difficulty: The difficulty of the problem.
        :param compare_func: The name of the comparison function.
        :param lang: The programming language of the code.
        """
        # Limit the number of concurrent executions based on the difficulty level.
        sem = self._execution_semaphores[difficulty.lower()]
        gen = self.test_generators[lang]

        async with sem:  # blocks until a semaphore is available

            # Create a temporary file to store the test runner file.
            with tempfile.NamedTemporaryFile(mode='w', suffix=gen.get_file_extension(lang), delete=False) as f:
                # Test data are pairs of test cases and its expected results.
                test_data = [
                    {"input": tc, "expected": er}
                    for tc, er in zip(test_cases, expected_results)
                ]
                sample_data = [
                    {"input": tc, "expected": er}
                    for tc, er in zip(sample_test_cases, sample_expected_results)
                ]
                import pdb; pdb.set_trace()
                base_name = os.path.basename(f.name).split('.')[0]
                file_content = gen.generate_test_file(code, base_name, method_name, test_data, sample_data, compare_func)
                f.write(file_content)
                file_path = f.name
            try:
                result = self.docker.run_container(lang, file_path, difficulty)

                # If all tests passed, get runtime analysis
                if result.all_cleared() and not settings.TESTING:
                    runtime_analysis = await runtime_analysis_service.analyze_code(code)
                    result.runtime_analysis = runtime_analysis

                return result
            finally:
                # Clean up the temporary file
                os.unlink(file_path)


code_execution = CodeExecutionService()
