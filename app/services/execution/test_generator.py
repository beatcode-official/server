import json
from typing import Dict, List
from abc import ABC, abstractmethod
from services.execution.templates import PYTHON_TEMPLATE, JAVA_TEMPLATE, CPP_TEMPLATE


class TestGenerator(ABC):
    """
    A class to generate test runner code for a given solution code, test data and compare function.
    """

    @abstractmethod
    def generate_test_file(
        self,
        code: str,
        file_name: str,
        method_name: str,
        test_data: List[Dict],
        sample_data: List[Dict],
        compare_func: str,
    ) -> str:
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

    def process_quotes(self, json_str: str) -> str:
        """
        Process quotes in a JSON string.
        """
        return json_str.replace('"', '\\"').replace(
            '\\\\"', '\\\\\\"'
        )  # cursed code alert


class PythonTestGenerator(TestGenerator):
    def generate_test_file(
        self,
        code: str,
        file_name: str,
        method_name: str,
        test_data: List[Dict],
        sample_data: List[Dict],
        compare_func: str,
    ) -> str:
        return PYTHON_TEMPLATE.format(
            code=code,
            method_name=method_name,
            compare_func=compare_func,
            test_data=json.dumps(test_data),
            sample_data=json.dumps(sample_data),
        )

    def get_file_extension(self, lang: str) -> str:
        return ".py"


class JavaTestGenerator(TestGenerator):
    def generate_test_file(
        self,
        code: str,
        file_name: str,
        method_name: str,
        test_data: List[Dict],
        sample_data: List[Dict],
        compare_func: str,
    ) -> str:
        MAX_STR_LEN = 60000
        test_data = self.process_quotes(json.dumps(test_data))
        sample_data = self.process_quotes(json.dumps(sample_data))
        if len(test_data) > MAX_STR_LEN:
            test_data = self.data_chunks(test_data)
        else:
            test_data = f'"{test_data}"'
        if len(sample_data) > MAX_STR_LEN:
            sample_data = self.data_chunks(test_data)
        else:
            sample_data = f'"{sample_data}"'

        return JAVA_TEMPLATE.format(
            code=code,
            file_name=file_name,
            method_name=method_name,
            compare_func=compare_func,
            test_data=test_data,
            sample_data=sample_data,
        )

    def get_file_extension(self, lang: str) -> str:
        return ".java"

    # Apparently string variables can only be 65k characters max in java
    def data_chunks(self, data: str) -> str:
        """Converts the data to a string of concatenated JSON strings."""
        MAX_LENGTH = 1000
        json_strings = []
        cur = 0
        while cur < len(data):
            if cur + MAX_LENGTH < len(data):
                next_chunk = data[cur : cur + MAX_LENGTH]
            else:
                next_chunk = data[cur:]
            json_strings.append(next_chunk)
            cur += MAX_LENGTH
        chunks = ''.join(['.append("' + s + '")' for s in json_strings])
        return f"new StringBuilder(){chunks}.toString()"

class CppTestGenerator(TestGenerator):
    def generate_test_file(
        self,
        code: str,
        file_name: str,
        method_name: str,
        test_data: List[Dict],
        sample_data: List[Dict],
        compare_func: str,
    ) -> str:
        args_init, args_param = self.process_args(test_data[0]["input"])
        return CPP_TEMPLATE.format(
            code=code,
            file_name=file_name,
            method_name=method_name,
            compare_func=compare_func,
            test_data=self.process_quotes(json.dumps(test_data)),
            sample_data=self.process_quotes(json.dumps(sample_data)),
            args_init=args_init,
            args_param=args_param,
        )

    def process_args(self, args: str) -> (str, str):
        args_list = args.split()
        init_lines = []
        params = []
        for i in range(len(args_list)):
            var_name = f"arg{i+1}"
            line = f"auto {var_name} = args[{i}].get<typename arg_type<{i}, Method_t>::type>();"
            init_lines.append(line)
            params.append(var_name)
        # initializing and inserting these auto arguments
        args_init = "\n".join(init_lines)
        args_param = ", ".join(params)
        return args_init, args_param

    def get_file_extension(self, lang: str) -> str:
        return ".cpp"
