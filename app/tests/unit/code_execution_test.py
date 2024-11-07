import asyncio
import os
import sys
from pprint import pprint

import pytest

# fmt: off
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from services.execution.service import CodeExecutionService
# fmt: on


@pytest.fixture
def executor():
    return CodeExecutionService()


@pytest.fixture
def valid_solution():
    return """
class Solution:
    def add(self, a: int, b: int) -> int:
        return a + b
    
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        seen = {}
        for i, num in enumerate(nums):
            complement = target - num
            if complement in seen:
                return [seen[complement], i]
            seen[num] = i
        return []
"""


@pytest.fixture
def invalid_syntax_solution():
    return """
class Solution:
    def add(self, a: int, b: int) -> int
        return a + b  
"""


@pytest.fixture
def undefined_variable_solution():
    return """
class Solution:
    def add(self, a: int, b: int) -> int:
        return n
"""


@pytest.fixture
def infinite_loop_solution():
    return """
class Solution:
    def add(self, a: int, b: int) -> int:
        while True:
            pass
        return a + b
"""


@pytest.fixture
def memory_heavy_solution():
    return """
class Solution:
    def add(self, a: int, b: int) -> int:
        x = [i for i in range(10**8)]  
        return a + b
"""


@pytest.mark.asyncio
async def test_successful_execution(executor, valid_solution):
    result = await executor.execute_code(
        code=valid_solution,
        test_cases=["add(1, 2)", "add(0, 0)", "add(-1, 1)"],
        expected_results=["3", "0", "0"],
        difficulty="easy",
        compare_func="return str(result) == expected"
    )

    assert result.success
    assert len(result.test_results) == 3
    assert all(test["passed"] for test in result.test_results)

    assert True


@pytest.mark.asyncio
async def test_failed_test_cases(executor, valid_solution):
    result = await executor.execute_code(
        code=valid_solution,
        test_cases=["add(1, 2)", "add(0, 0)"],
        expected_results=["4", "1"],
        difficulty="easy",
        compare_func="return str(result) == expected"
    )

    assert result.success
    assert len(result.test_results) == 2
    assert not any(test["passed"] for test in result.test_results)
    assert all(test["error"] is None for test in result.test_results)


@pytest.mark.asyncio
async def test_syntax_error(executor, invalid_syntax_solution):
    result = await executor.execute_code(
        code=invalid_syntax_solution,
        test_cases=["add(1, 2)"],
        expected_results=["3"],
        difficulty="easy",
        compare_func="return str(result) == expected"
    )

    assert not result.success
    assert "SyntaxError" in result.message


@pytest.mark.asyncio
async def test_undefined_error(executor, undefined_variable_solution):
    result = await executor.execute_code(
        code=undefined_variable_solution,
        test_cases=["add(1, 2)", "add(2, 2)"],
        expected_results=["3", "4"],
        difficulty="easy",
        compare_func="return str(result) == expected"
    )

    assert result.success
    assert len(result.test_results) == 2
    assert not all(test["passed"] for test in result.test_results)
    assert all(test["error"] is not None for test in result.test_results)


@pytest.mark.asyncio
async def test_timeout(executor, infinite_loop_solution):
    result = await executor.execute_code(
        code=infinite_loop_solution,
        test_cases=["add(1, 2)"],
        expected_results=["3"],
        difficulty="easy",
        compare_func="return str(result) == expected"
    )

    assert not result.success
    assert "Time Limit Exceeded" in result.message


@pytest.mark.asyncio
async def test_memory_limit(executor, memory_heavy_solution):
    result = await executor.execute_code(
        code=memory_heavy_solution,
        test_cases=["add(1, 2)"],
        expected_results=["3"],
        difficulty="easy",
        compare_func="return str(result) == expected"
    )

    assert not result.success
    assert "Memory Limit Exceeded" in result.message


@pytest.mark.asyncio
async def test_complex_problem(executor, valid_solution):
    result = await executor.execute_code(
        code=valid_solution,
        test_cases=[
            "twoSum([2,7,11,15], 9)",
            "twoSum([3,2,4], 6)",
            "twoSum([3,3], 6)"
        ],
        expected_results=[
            "[0,1]",
            "[1,2]",
            "[0,1]"
        ],
        difficulty="easy",
        compare_func="""
def normalize(s):
    return str(sorted(eval(s)))
return normalize(str(result)) == normalize(expected)
"""
    )

    assert result.success
    assert len(result.test_results) == 3
    assert all(test["passed"] for test in result.test_results)


@pytest.mark.asyncio
async def test_concurrent_executions(executor, valid_solution):
    tasks = []
    for _ in range(20):
        tasks.append(
            executor.execute_code(
                code=valid_solution,
                test_cases=["add(1, 2)"],
                expected_results=["3"],
                difficulty="hard",
                compare_func="return str(result) == expected"
            )
        )

    results = await asyncio.gather(*tasks)
    assert all(r.success for r in results)
    assert len(results) == 20


def test_different_difficulty_semaphores(executor):
    assert executor._execution_semaphores["easy"]._value > \
        executor._execution_semaphores["medium"]._value > \
        executor._execution_semaphores["hard"]._value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
