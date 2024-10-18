
import unittest
import sys
import os

# fmt: off
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.services.docker_execution_service import DockerExecutionService
# fmt: on


class TestDockerExec(unittest.TestCase):
    def test_simple_execution(self):
        service = DockerExecutionService()

        code = "def add(a, b):\n    return a + b"
        test_cases = ["add(1, 2)", "add(-1, 1)", "add(0, 0)"]
        expected_outputs = ["3", "0", "0"]
        comparison_function = "result == int(expected)"

        resp = service.execute_code(code, test_cases, expected_outputs, comparison_function)
        self.assertEqual(resp['status'], 'success')
        self.assertEqual(resp['passed_tests'], 3)

    def test_timeout(self):
        service = DockerExecutionService(timeout=2)

        code = "import time\ndef add(a, b):\n    time.sleep(5)\n    return a + b"
        test_cases = ["add(1, 2)"]
        expected_outputs = ["3"]
        comparison_function = "result == int(expected)"

        resp = service.execute_code(code, test_cases, expected_outputs, comparison_function)
        self.assertEqual(resp['status'], 'error')
        self.assertEqual(resp['passed_tests'], 0)
        self.assertEqual("timed out" in resp['message'], True)

    def test_wrong_method(self):
        service = DockerExecutionService()

        code = "def adda(a, b):\n    return a + b"
        test_cases = ["add(1, 2)", "add(-1, 1)", "add(0, 0)"]
        expected_outputs = ["3", "0", "0"]
        comparison_function = "result == int(expected)"

        resp = service.execute_code(code, test_cases, expected_outputs, comparison_function)
        self.assertEqual(resp['status'], 'error')
        self.assertEqual(resp['passed_tests'], 0)
        self.assertEqual("NameError" in resp['message'], True)

    def test_broken_code(self):
        service = DockerExecutionService()

        code = "def add(a, b):\n    return JOE"
        test_cases = ["add(1, 2)", "add(-1, 1)", "add(0, 0)"]
        expected_outputs = ["3", "0", "0"]
        comparison_function = "result == int(expected)"

        resp = service.execute_code(code + "a", test_cases, expected_outputs, comparison_function)
        self.assertEqual(resp['status'], 'error')
        self.assertEqual(resp['passed_tests'], 0)
        self.assertEqual("NameError" in resp['message'], True)


if __name__ == '__main__':
    unittest.main()
