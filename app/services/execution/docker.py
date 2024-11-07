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
        self.docker_image = settings.DOCKER_IMAGE
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

    def run_container(self, file_path: str, difficulty: str) -> ExecutionResult:
        """
        Run the code in a Docker container.

        :param file_path: The path to the file to run.
        :param difficulty: The difficulty of the problem.
        :return: The result of the execution.
        """
        # Get the memory and time limits for the difficulty level.
        memory_limit, time_limit = self._docker_settings[difficulty.lower()]

        try:
            # Run the container with the specified constraints
            container = self.client.containers.run(
                self.docker_image,
                ["python3", os.path.basename(file_path)],
                volumes={
                    os.path.dirname(file_path): {
                        "bind": "/code",  # bind the directory to /code in the container
                        "mode": "ro",  # read only
                    }
                },
                working_dir="/code",
                mem_limit=f"{memory_limit}m",
                nano_cpus=int(self.docker_cpu_limit * 1e9),
                network_disabled=True,
                read_only=True,
                detach=True,  # run the container in the background
                remove=True,  # remove the container after it stops
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
                        test_results=execution_data["test_results"],
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
