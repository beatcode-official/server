import asyncio
import json
import os
import tempfile
from typing import Dict, List, Optional

import docker
import docker.errors
from core.config import settings


class ExecutionResult:
    def __init__(
        self,
        success: bool,
        message: Optional[str] = None,
        test_results: Optional[List[Dict]] = None,
        execution_time: Optional[float] = None,
    ):
        self.success = success
        self.message = message
        self.test_results = test_results
        self.execution_time = execution_time

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "message": self.message,
            "test_results": self.test_results,
            "execution_time": self.execution_time,
            "passed_count": len([t for t in self.test_results if t.get("passed", False)]) if self.test_results else 0,
            "total_count": len(self.test_results) if self.test_results else 0,
        }


class CodeExecutionService:
    def __init__(self):
        self.client = docker.from_env()
        self._execution_semaphores = {
            "easy": asyncio.Semaphore(settings.MAX_CONCURRENT_EASY),
            "medium": asyncio.Semaphore(settings.MAX_CONCURRENT_MEDIUM),
            "hard": asyncio.Semaphore(settings.MAX_CONCURRENT_HARD),
        }
        self._docker_settings = {
            "easy": [settings.DOCKER_MEMORY_LIMIT_EASY, settings.DOCKER_TIME_LIMIT_EASY],
            "medium": [settings.DOCKER_MEMORY_LIMIT_MEDIUM, settings.DOCKER_TIME_LIMIT_MEDIUM],
            "hard": [settings.DOCKER_MEMORY_LIMIT_HARD, settings.DOCKER_TIME_LIMIT_HARD],
        }

    async def execute_code(
        self,
        code: str,
        test_cases: List[str],
        expected_results: List[str],
        difficulty: str,
        compare_func: str,
    ) -> ExecutionResult:
        sem = self._execution_semaphores[difficulty.lower()]
        memory_limit, time_limit = self._docker_settings[difficulty.lower()]

        async with sem:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                test_data = [
                    {"input": tc, "expected": er}
                    for tc, er in zip(test_cases, expected_results)
                ]

                f.write(code + '\n\n')
                f.write(self._generate_test_runner(test_data, compare_func))
                file_path = f.name

            try:
                container = self.client.containers.run(
                    settings.DOCKER_IMAGE,
                    ["python3", os.path.basename(file_path)],
                    volumes={
                        os.path.dirname(file_path): {
                            "bind": "/code",
                            "mode": "ro",
                        }
                    },
                    working_dir="/code",
                    mem_limit=f"{memory_limit}m",
                    nano_cpus=int(settings.DOCKER_CPU_LIMIT * 1e9),
                    network_disabled=True,
                    read_only=True,
                    detach=True,
                    remove=True,
                )

                try:
                    result = container.wait(timeout=time_limit / 1000)
                    logs = container.logs().decode('utf-8')

                    if result["StatusCode"] != 0:
                        return ExecutionResult(
                            success=False,
                            message="Runtime Error: " + logs.strip(),
                        )

                    if "EXECUTION_RESULTS:" in logs:
                        execution_data = json.loads(
                            logs.split("EXECUTION_RESULTS:")[1].strip()
                        )

                        return ExecutionResult(
                            success=True,
                            test_results=execution_data["test_results"],
                            execution_time=execution_data["execution_time"],
                        )

                    return ExecutionResult(
                        success=False,
                        message="Invalid execution output format",
                    )

                except docker.errors.ContainerError:
                    return ExecutionResult(
                        success=False,
                        message="Container execution failed",
                    )

                except docker.errors.NotFound:
                    return ExecutionResult(
                        success=False,
                        message="Container stopped unexpectedly",
                    )
            except Exception as e:
                return ExecutionResult(
                    success=False,
                    message=f"Execution error: {str(e)}",
                )

            finally:
                try:
                    container.remove(force=True)
                except:
                    pass
                os.unlink(file_path)

    def _generate_test_runner(self, test_data: List[Dict], compare_func: str) -> str:
        compare_func = "\n    ".join(compare_func.splitlines())
        return f"""
import time
import json
import traceback
from typing import Any

def compare_results(result: Any, expected: str) -> bool:
    {compare_func}
    
class TestResult:
    def __init__(self, test_input: str, passed: bool, output: Any = None, error: str = None):
        self.test_input = test_input
        self.passed = passed
        self.output = str(output) if output is not None else None
        self.error = error
        
    def to_dict(self):
        return {{
            "test_input": self.test_input,
            "passed": self.passed,
            "output": self.output,
            "error": self.error,
        }}
        
def run_tests(solution, test_data):
    results = []
    start_time = time.time()
    
    for test in test_data:
        try:
            result = eval(f"solution.{{test['input']}}")
            passed = compare_results(result, test['expected'])
            results.append(TestResult(
                test_input=test['input'],
                passed=passed,
                output=result   
            ).to_dict())
        except Exception as e:
            results.append(TestResult(
                test_input=test['input'],
                passed=False,
                error=str(e) + '\\n' + traceback.format_exc()
            ).to_dict())
            
    execution_time = time.time() - start_time
    return {{"test_results": results, "execution_time": execution_time}}
    
if __name__ == "__main__":
    test_data = {json.dumps(test_data)}
    try:
        solution = Solution()
        results = run_tests(solution, test_data)
        print("EXECUTION_RESULTS:", json.dumps(results))
    except Exception as e:
        print("GLOBAL_ERROR:", str(e) + '\\n' + traceback.format_exc())
"""
