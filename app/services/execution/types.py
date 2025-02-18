from typing import Dict, List, Optional


class ExecutionResult:
    """
    A class to represent the result of an execution.
    """

    def __init__(
        self,
        success: bool,
        message: Optional[str] = None,
        test_results: Optional[List[Dict]] = None,
        sample_results: Optional[List[Dict]] = None,
        summary: Optional[Dict] = None,
        runtime_analysis: Optional[str] = None,
    ):
        self.success = success
        self.message = message
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
