import json
from typing import Dict, List
from abc import ABC, abstractmethod
from services.execution.templates import PYTHON_TEMPLATE, JAVA_TEMPLATE, CPP_TEMPLATE

class TestGenerator(ABC):
    """
    A class to generate test runner code for a given solution code, test data and compare function.
    """

    @abstractmethod
    def generate_test_file(self, code: str, method_name: str, test_data: List[Dict], sample_data: List[Dict], compare_func: str) -> str:
        """
        Generate test runner code for a given solution code, test data and compare function.

        :param code: The solution code.
        :param method_name: The solution's main function name.
        :param test_data: The test data.
        :param compare_func: The compare function.
        """
    
    @abstractmethod
    def get_file_extension(self, lang: str) -> str:
        """
        Get the file extension for the given language.
        """        

class PythonTestGenerator(TestGenerator):
    def generate_test_file(self, code: str, method_name: str, test_data: List[Dict], sample_data: List[Dict], compare_func: str) -> str:
        test_data = self.format_test_data(method_name, test_data)
        sample_data = self.format_test_data(method_name, sample_data)
        return PYTHON_TEMPLATE.format(
            code=code,
            compare_func=compare_func,
            test_data=json.dumps(test_data),
            sample_data=json.dumps(sample_data),
        )
    
    def format_test_data(self, method_name: str, test_data: List[Dict]):
        formatted = []
        for test in test_data:
            segments = test["input"].split("--arg")
            segments = [s.strip() for s in segments if s.strip()]
            params = []
            for s in segments:
                if "=" in s:
                    _, val = s.split("=", 1)
                    params.append(val.strip())
            formatted.append({
                "input": f"{method_name}({', '.join(params)})",
                "expected": test["expected"]
            })
        return formatted

    def get_file_extension(self, lang: str) -> str:
        return ".py"

class JavaTestGenerator(TestGenerator):
    def generate_test_file(self, code: str, method_name: str, test_data: List[Dict], sample_data: List[Dict], compare_func: str) -> str:
        test_data = self.format_test_data(method_name, test_data)
        sample_data = self.format_test_data(method_name, sample_data)
        return JAVA_TEMPLATE.format(
            code=code,
            compare_func=compare_func,
            test_data=json.dumps(test_data),
            sample_data=json.dumps(sample_data),
        )
    
    def format_test_data(self, method_name: str, test_data: List[Dict]):
        #TODO: Format array and objects
        formatted = []
        for test in test_data:
            segments = test["input"].split("--arg")
            segments = [s.strip() for s in segments if s.strip()]
            params = []
            for s in segments:
                if "=" in s:
                    _, val = s.split("=", 1)
                    params.append(val.strip())
            formatted.append({
                "input": f"{method_name}({', '.join(params)})",
                "expected": test["expected"]
            })
        return formatted

    def get_file_extension(self, lang: str) -> str:
        return ".java"

class CppTestGenerator(TestGenerator):
    def generate_test_file(self, code: str, method_name: str, test_data: List[Dict], sample_data: List[Dict], compare_func: str) -> str:
        test_data = self.format_test_data(method_name, test_data)
        sample_data = self.format_test_data(method_name, sample_data)
        return CPP_TEMPLATE.format(
            code=code,
            compare_func=compare_func,
            test_data=json.dumps(test_data),
            sample_data=json.dumps(sample_data),
        )
    
    def format_test_data(self, method_name: str, test_data: List[Dict]):
        #TODO: Format arrays and objects
        formatted = []
        for test in test_data:
            segments = test["input"].split("--arg")
            segments = [s.strip() for s in segments if s.strip()]
            params = []
            for s in segments:
                if "=" in s:
                    _, val = s.split("=", 1)
                    params.append(val.strip())
            formatted.append({
                "input": f"{method_name}({', '.join(params)})",
                "expected": test["expected"]
            })
        return formatted

    def get_file_extension(self, lang: str) -> str:
        return ".cpp"
