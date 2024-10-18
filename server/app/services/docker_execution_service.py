import os
import shutil
import tempfile
import threading
import uuid
from typing import List

import docker


class DockerExecutionService:
    def __init__(self, limit: int = 5, mem_limit: str = "128m", cpu_period: int = 100000, cpu_quota: int = 50000, timeout: int = 5):
        """
        A service to execute code in a docker container. Limits the number of concurrent docker containers that can be run through a semaphore.

        Args:
            limit (int): The number of concurrent docker containers that can be run
            mem_limit (str): The memory limit for the docker container
            cpu_period (int): The CPU period for the docker container
            cpu_quota (int): The CPU quota for the docker container
            timeout (int): The timeout for the docker container execution
        """
        self.docker_client = docker.from_env()
        self.mem_limit = mem_limit
        self.cpu_period = cpu_period
        self.cpu_quota = cpu_quota
        self.timeout = timeout
        self.semaphore = threading.Semaphore(limit)

    def execute_code(self, code: str, test_cases: List[str], expected_outputs: List[str], compare_func: str) -> int:
        """
        Executes the code in a docker container and compares the output with the expected output.

        Args:
            code (str): The code to execute
            test_cases (List[str]): The test cases to run
            expected_outputs (List[str]): The expected outputs for the test cases
            compare_func (str): The function to compare the output with the expected output

        Returns:
            dictionary: The result of the execution, containing the status, passed tests, and message
        """
        with self.semaphore:  # Acquire the semaphore
            container = None
            temp_dir = None

            try:
                temp_dir = tempfile.mkdtemp()
                script = self._prepare_script(code, test_cases, expected_outputs, compare_func)

                file_name = f"temp_{uuid.uuid4().hex}.py"
                file_path = os.path.join(temp_dir, file_name)

                with open(file_path, "w") as f:
                    f.write(script)

                container = self.docker_client.containers.run(
                    "python:3.11-alpine",
                    ["python", f"/code/{file_name}"],
                    detach=True,
                    mem_limit=self.mem_limit,
                    cpu_period=self.cpu_period,
                    cpu_quota=self.cpu_quota,
                    volumes={temp_dir: {'bind': '/code', 'mode': 'ro'}}
                )

                result = container.wait(timeout=self.timeout)
                logs = container.logs().decode("utf-8").strip()

                if result["StatusCode"] != 0:
                    return {
                        "status": "error",
                        "passed_tests": 0,
                        "message": logs
                    }
                else:
                    return {
                        "status": "success",
                        "passed_tests": int(logs),
                        "message": ""
                    }
            except Exception as e:
                return {
                    "status": "error",
                    "passed_tests": 0,
                    "message": str(e)
                }
            finally:
                if container:
                    container.remove(force=True)
                if temp_dir and os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)

    def _prepare_script(self, code: str, test_cases: List[str], expected_outputs: List[str], compare_func: str) -> str:
        """
        Prepares the script that will be executed in the docker container.

        Args:
            code (str): The code to execute
            test_cases (List[str]): The test cases to run
            expected_outputs (List[str]): The expected outputs for the test cases
            compare_func (str): The function to compare the output with the expected output

        Returns:
            str: The prepared script
        """
        script = f"""
{code}

def run_tests():
    passed_tests = 0
    test_cases = {test_cases}
    expected_outputs = {expected_outputs}
    
    for i, (test_case, expected) in enumerate(zip(test_cases, expected_outputs)):
        result = eval(test_case)
        if {compare_func}:
            passed_tests += 1
    
    print(passed_tests)

if __name__ == "__main__":
    run_tests()
"""

        return script
