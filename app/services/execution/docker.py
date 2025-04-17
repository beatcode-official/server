import json
import os
import traceback

from core.config import settings
from services.execution.types import ExecutionResult

import docker.errors


class DockerRunner:
    """
    A class to run code in a Docker container.
    """

    def __init__(self, client: docker.DockerClient):
        self.client = client
        self.docker_image = {
            "python": settings.DOCKER_IMAGE_PYTHON,
            "java": settings.DOCKER_IMAGE_JAVA,
            "cpp": settings.DOCKER_IMAGE_CPP,
        }
        self.docker_cpu_limit = settings.DOCKER_CPU_LIMIT
        self._docker_settings = {}
        for lang in self.docker_image.keys():
            mem_limits = [
                int(x)
                for x in getattr(settings, f"DOCKER_{lang.upper()}_MEMORY_LIMIT").split(
                    ","
                )
            ]
            time_limits = [
                int(x)
                for x in getattr(settings, f"DOCKER_{lang.upper()}_TIME_LIMIT").split(
                    ","
                )
            ]
            self._docker_settings[lang] = {
                "easy": (mem_limits[0], time_limits[0]),
                "medium": (mem_limits[1], time_limits[1]),
                "hard": (mem_limits[2], time_limits[2]),
            }
        self.last_logs = ""
        self.last_stderr = ""
        self.last_status_code = 0

    def get_run_commands(self, lang: str, file_path: str) -> list:
        """
        Get the command to run the code in a Docker container.

        :param lang: The language of the code.
        :param file_path: The path to the file to run.
        :return: The command to run the code in a Docker container.
        """
        file_name = os.path.basename(file_path)
        base_name = file_name.split(".")[0]

        if lang == "python":
            return ["python", file_name]

        # Needs to compile first before running unlike Python
        elif lang == "java":
            return [
                "sh",
                "-c",
                f"javac -cp /lib/*:/code {file_name} && java -cp /lib/*:/code {base_name}",
            ]

        elif lang == "cpp":
            return [
                "sh",
                "-c",
                f"g++ -std=c++17 -o {base_name} {file_name} -ljsoncpp && ./{base_name}",
            ]

        raise ValueError(f"Unsupported language: {lang}")

    def run_container(
        self, lang: str, file_path: str, difficulty: str, line_offset: int
    ) -> ExecutionResult:
        """
        Run the code in a Docker container.

        :param lang: The language of the code.
        :param file_path: The path to the file to run.
        :param difficulty: The difficulty of the problem.
        :param line_offset: The line offset for error logs.
        :return: The result of the execution.
        """
        # Get the memory and time limits for the difficulty level.
        memory_limit, time_limit = self._docker_settings[lang][difficulty.lower()]
        dir_path = os.path.dirname(file_path)
        if not dir_path:
            dir_path = "."

        try:
            # Run the container with the specified constraints
            container = self.client.containers.run(
                self.docker_image[lang],
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
                self.last_logs = container.logs().decode("utf-8")
                self.last_stderr = container.logs(stdout=False, stderr=True).decode(
                    "utf-8"
                )
                self.last_status_code = result["StatusCode"]

                # Check if the container stopped unexpectedly
                if result["StatusCode"] != 0:
                    if (
                        result["StatusCode"] == 137
                    ):  # SIGKILL - likely fired when memory limit is exceeded
                        return ExecutionResult(
                            success=False,
                            message="Runtime Error Detected: Memory Limit Exceeded",
                        )
                    return ExecutionResult(
                        success=False,
                        message="Runtime Error Detected\n" + self.last_logs.strip(),
                        line_offset=line_offset,
                    )

                if self.last_stderr.strip():
                    return ExecutionResult(
                        success=False,
                        message="Runtime Error Detected\n" + self.last_stderr.strip(),
                        line_offset=line_offset,
                    )

                base_name = os.path.basename(file_path).split(".")[0]
                results_file = os.path.join(dir_path, f"{base_name}-results.txt")

                if os.path.exists(results_file):
                    with open(results_file, "r") as f:
                        execution_data = json.load(f)
                    os.remove(results_file)
                    return ExecutionResult(
                        success=True,
                        test_results=execution_data["hidden_results"]["test_results"],
                        sample_results=execution_data["sample_results"]["test_results"],
                        line_offset=line_offset,
                    )
                else:
                    return ExecutionResult(
                        success=False,
                        message="Test Runner Error: Results file not found\n"
                        + self.last_logs.strip(),
                    )
            except Exception as e:
                # Check for timeout, else raise the exception
                self.last_logs = container.logs().decode("utf-8")
                self.last_stderr = container.logs(stdout=False, stderr=True).decode(
                    "utf-8"
                )
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
                message="Execution Error",
            )

    def get_last_logs(self) -> str:
        """Returns combined stdout/stderr logs from last container run"""
        return self.last_logs

    def get_last_errors(self) -> str:
        """Returns stderr logs from last container run"""
        return self.last_stderr

    def get_last_status(self) -> int:
        """Returns exit status code from last container run"""
        return self.last_status_code
