import json
from typing import Dict, List


class TestGenerator:
    """
    A class to generate test runner code for a given solution code, test data and compare function.
    """

    def generate_test_runner(self, code: str, test_data: List[Dict], compare_func: str) -> str:
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
        test_input: str,
        expected: str,
        passed: bool,
        output: Any = None,
        error: str = None,
    ):
        self.test_input = test_input
        self.expected = expected
        self.output = str(output) if output is not None else None
        self.passed = passed
        self.error = error
        
    def to_dict(self):
        return {{
            "test_input": self.test_input,
            "expected": self.expected,
            "output": self.output,
            "passed": self.passed,
            "error": self.error,
        }}
        
def run_tests(solution, test_data):
    results = []
    
    for test in test_data:
        try:
            result = eval(f"solution.{{test['input']}}")
            passed = compare_results(result, test['expected'])
            results.append(TestResult(
                test_input=test['input'],
                expected=test['expected'],
                output=result,
                passed=passed,
            ).to_dict())
        except Exception as e:
            results.append(TestResult(
                test_input=test['input'],
                expected=test['expected'],
                passed=False,
                error=traceback.format_exc(),
            ).to_dict())
            
    return {{
        "test_results": results,
        "summary": {{
            "total_tests": len(results),
            "passed_tests": len([r for r in results if r["passed"]]),
        }}
    }}
    
if __name__ == "__main__":
    test_data = {json.dumps(test_data)}
    try:
        solution = Solution()
        results = run_tests(solution, test_data)
        print("EXECUTION_RESULTS:", json.dumps(results))
    except Exception as e:
        print("GLOBAL_ERROR:\\n" + traceback.format_exc())
"""
