import json
from typing import Dict, List


class TestGenerator:
    """
    A class to generate test runner code for a given solution code, test data and compare function.
    """

    def generate_test_runner(self, code: str, test_data: List[Dict], sample_data: List[Dict], compare_func: str) -> str:
        """
        Generate test runner code for a given solution code, test data and compare function.

        :param code: The solution code.
        :param test_data: The test data.
        :param compare_func: The compare function.
        """
        compare_func = "\n    ".join(compare_func.splitlines())
        return f"""
import json
import traceback
from typing import *

{code}

def compare_results(result: Any, expected: str) -> bool:
    {compare_func}
    
class TestResult:
    def __init__(
        self,
        expected: str,
        passed: bool,
        output: Any = None,
        error: str = None,
        input_data: str = None,
    ):
        self.expected = expected
        self.output = str(output) if output is not None else None
        self.passed = passed
        self.error = error
        self.input_data = input_data
        
    def to_dict(self, include_input: bool = True):
        result = {{
            "expected": self.expected,
            "output": self.output,
            "passed": self.passed,
            "error": self.error,
        }}
        if include_input:
            result["input_data"] = self.input_data
        return result
        
        
def run_tests(solution, test_data, is_sample: bool = False):
    results = []
    
    for test in test_data:
        try:
            result = eval(f"solution.{{test['input']}}")
            passed = compare_results(result, test['expected'])
            results.append(TestResult(
                expected=test['expected'],
                output=result,
                passed=passed,
                input_data=test['input'],
            ).to_dict(include_input=is_sample))
        except Exception as e:
            results.append(TestResult(
                expected=test['expected'],
                passed=False,
                error=traceback.format_exc(),
                input_data=test['input'],
            ).to_dict(include_input=is_sample))
            
    return {{
        "test_results": results,
        "summary": {{
            "total_tests": len(results),
            "passed_tests": len([r for r in results if r["passed"]]),
        }}
    }}
    
if __name__ == "__main__":
    test_data = {json.dumps(test_data)}
    sample_data = {json.dumps(sample_data)}
    try:
        solution = Solution()
        hidden_results = run_tests(solution, test_data, is_sample=False)
        sample_results = run_tests(solution, sample_data, is_sample=True)
        results = {{
            "hidden_results": hidden_results,
            "sample_results": sample_results
        }}
        print("EXECUTION_RESULTS:", json.dumps(results))
    except Exception as e:
        print("GLOBAL_ERROR:\\n" + traceback.format_exc())
"""
