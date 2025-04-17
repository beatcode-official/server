from typing import Any, Dict, List, Optional


class TestResult:
    def __init__(
        self,
        expected: str,
        passed: bool,
        output: Any = None,
        logs: str = None,
        error: str = None,
        input: str = None,
    ):
        self.expected = expected
        self.output = str(output) if output is not None else None
        self.passed = passed
        self.logs = logs
        self.error = error
        self.input = input

    def to_dict(self, is_sample: bool = True):
        result = {
            {
                "expected": self.expected,
                "output": self.output,
                "passed": self.passed,
                "error": self.error,
            }
        }
        if is_sample:
            result["logs"] = self.logs
            result["input"] = self.input
        return result


class ExecutionResult:
    """
    A class to represent the result of an execution.
    """

    def __init__(
        self,
        success: bool,
        message: Optional[str] = None,
        line_offset: Optional[int] = None,  # for error logs from templates
        test_results: Optional[List[TestResult]] = None,
        sample_results: Optional[List[TestResult]] = None,
        summary: Optional[Dict] = None,
        runtime_analysis: Optional[str] = None,
    ):
        self.success = success
        self.message = message
        self.line_offset = line_offset
        self.test_results = test_results
        self.sample_results = sample_results
        self.summary = summary
        self.runtime_analysis = runtime_analysis

    def all_cleared(self) -> bool:
        """
        Check if all tests passed.
        """
        return (
            all(t.get("passed", False) for t in self.test_results)
            if self.test_results
            else False
        )

    def to_dict(self) -> Dict:
        """
        Conversion method in case we need to serialize the object.
        """
        return {
            "success": self.success,
            "message": self.message,
            "line_offset": self.line_offset,
            "test_results": self.test_results,
            "sample_results": self.sample_results,
            "summary": self.summary
            or {
                "total_tests": len(self.test_results) if self.test_results else 0,
                "passed_tests": (
                    len([t for t in self.test_results if t.get("passed", False)])
                    if self.test_results
                    else 0
                ),
            },
            "runtime_analysis": self.runtime_analysis,
        }
