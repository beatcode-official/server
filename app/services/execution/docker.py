import json
import os
import traceback

import docker.errors
from core.config import settings
from services.execution.types import ExecutionResult


class DockerRunner:
    """
    A class to run code in a Docker container.
    """

    def __init__(self, client: docker.DockerClient):
        self.client = client
        self.docker_image_map = {
            "python": settings.DOCKER_IMAGE_PYTHON,
            "java": settings.DOCKER_IMAGE_JAVA,
            "cpp": settings.DOCKER_IMAGE_CPP,
        }
        self.docker_cpu_limit = settings.DOCKER_CPU_LIMIT
        easy_mem, medium_mem, hard_mem = [
            int(x) for x in settings.DOCKER_MEMORY_LIMIT.split(",")
        ]
        easy_time, medium_time, hard_time = [
            int(x) for x in settings.DOCKER_TIME_LIMIT.split(",")
        ]
        self._docker_settings = {
            "easy": [easy_mem, easy_time],
            "medium": [medium_mem, medium_time],
            "hard": [hard_mem, hard_time],
        }
    
    def get_run_commands(self, lang: str, file_path: str) -> list:
        """
        Get the command to run the code in a Docker container.

        :param lang: The language of the code.
        :param file_path: The path to the file to run.
        :return: The command to run the code in a Docker container.
        """
        file_name = os.path.basename(file_path)
        base_name = file_name.split('.')[0]
    
        if lang == "python":
            return ["python", file_name]
        
        # Needs to compile first before running unlike Python
        elif lang == "java":
            return [
                "sh", "-c",
                f"javac -cp /lib/*:/code {file_name} && java -cp /lib/*:/code {base_name}"
            ]
        
        elif lang == "cpp":
            return [
                "sh", "-c",
                f"g++ -std=c++17 -o {base_name} {file_name} -ljsoncpp && ./{base_name}"
            ]
        
        raise ValueError(f"Unsupported language: {lang}")

    def run_container(self, lang: str, file_path: str, difficulty: str) -> ExecutionResult:
        """
        Run the code in a Docker container.

        :param file_path: The path to the file to run.
        :param difficulty: The difficulty of the problem.
        :return: The result of the execution.
        """
        # Get the memory and time limits for the difficulty level.
        memory_limit, time_limit = self._docker_settings[difficulty.lower()]
        dir_path = os.path.dirname(file_path)
        if not dir_path:
            dir_path = "."

        try:
            # Run the container with the specified constraints
            container = self.client.containers.run(
                self.docker_image_map[lang],
                self.get_run_commands(lang, file_path),
                volumes={
                    dir_path: {
                        "bind": "/code",  # bind the directory to /code in the container
                        "mode": "rw",  # read write
                    }
                },
                working_dir="/code",
                mem_limit=f"{memory_limit}m",
                nano_cpus=int(self.docker_cpu_limit * 1e9),
                network_disabled=True,
                privileged=False,
                # read_only=True,
                detach=True,  # run the container in the background
            )

            try:
                # Wait for the container to finish and get the logs
                result = container.wait(timeout=time_limit / 1000)
                logs = container.logs().decode('utf-8')

                # Check if the container stopped unexpectedly
                if result["StatusCode"] != 0:
                    if result["StatusCode"] == 137:  # SIGKILL - likely fired when memory limit is exceeded
                        return ExecutionResult(
                            success=False,
                            message="Runtime Error Detected: Memory Limit Exceeded",
                        )
                    return ExecutionResult(
                        success=False,
                        message="Runtime Error Detected\n" + logs.strip(),
                    )

                # When successful, the test runner returns 'EXECUTION_RESULTS:' in its
                # output, followed by a JSON object with the test results and execution time.
                if "EXECUTION_RESULTS:" in logs:
                    execution_data = json.loads(
                        logs.split("EXECUTION_RESULTS:")[1].strip()
                    )

                    return ExecutionResult(
                        success=True,
                        test_results=execution_data["hidden_results"]["test_results"],
                        sample_results=execution_data["sample_results"]["test_results"],
                    )

                # If the success string is not found, means an exception occurred
                return ExecutionResult(
                    success=False,
                    message="Test Runner Error Detected\n" + logs.strip(),
                )
            except Exception as e:
                # Check for timeout, else raise the exception
                if "timed out" in str(e):
                    return ExecutionResult(
                        success=False,
                        message="Runtime Error Detected: Time Limit Exceeded",
                    )
                else:
                    raise e

            finally:
                # Remove the container after it stops
                try:
                    container.remove(force=True)
                except:
                    pass

        except Exception as _:
            print(traceback.format_exc())
            return ExecutionResult(
                success=False,
                message=f"Execution Error",
            )
