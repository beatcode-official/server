import asyncio
import os
import sys
from pprint import pprint

import pytest

# fmt: off
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from services.execution.service import CodeExecutionService
# fmt: on

class TestPython:
    @pytest.fixture
    def executor(self):
        return CodeExecutionService()

    @pytest.fixture
    def valid_solution(self):
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
    def invalid_syntax_solution(self):
        return """
class Solution:
    def add(self, a: int, b: int) -> int
        return a + b  
"""

    @pytest.fixture
    def undefined_variable_solution(self):
        return """
class Solution:
    def add(self, a: int, b: int) -> int:
        return n
"""

    @pytest.fixture
    def infinite_loop_solution(self):
        return """
class Solution:
    def add(self, a: int, b: int) -> int:
        while True:
            pass
        return a + b
"""

    @pytest.fixture
    def memory_heavy_solution(self):
        return """
class Solution:
    def add(self, a: int, b: int) -> int:
        x = [i for i in range(10**8)]  
        return a + b
"""

    @pytest.mark.asyncio
    async def test_successful_execution(self, executor, valid_solution):
        result = await executor.execute_code(
            code=valid_solution,
            method_name="add",
            test_cases=["--arg1=1 --arg2=2", "--arg1=0 --arg2=0", "--arg1=-1 --arg2=1"],
            expected_results=["3", "0", "0"],
            sample_test_cases=["--arg1=1 --arg2=2", "--arg1=0 --arg2=0", "--arg1=-1 --arg2=1"],
            sample_expected_results=["3", "0", "0"],
            difficulty="easy",
            compare_func="return result == int(expected)"
        )

        assert result.success
        assert len(result.test_results) == 3
        assert all(test["passed"] for test in result.test_results)

    @pytest.mark.asyncio
    async def test_failed_test_cases(self, executor, valid_solution):
        result = await executor.execute_code(
            code=valid_solution,
            method_name="add",
            test_cases=["--arg1=1 --arg2=2", "--arg1=0 --arg2=0"],
            expected_results=["4", "1"],
            sample_test_cases=["--arg1=1 --arg2=2", "--arg1=0 --arg2=0", "--arg1=-1 --arg2=1"],
            sample_expected_results=["3", "0", "0"],
            difficulty="easy",
            compare_func="return result == int(expected)"
        )

        assert result.success
        assert len(result.test_results) == 2
        assert not any(test["passed"] for test in result.test_results)
        assert all(test["error"] is None for test in result.test_results)

    @pytest.mark.asyncio
    async def test_syntax_error(self, executor, invalid_syntax_solution):
        result = await executor.execute_code(
            code=invalid_syntax_solution,
            method_name="add",
            test_cases=["--arg1=1 --arg2=2"],
            expected_results=["3"],
            sample_test_cases=["--arg1=1 --arg2=2", "--arg1=0 --arg2=0", "--arg1=-1 --arg2=1"],
            sample_expected_results=["3", "0", "0"],
            difficulty="easy",
            compare_func="return result == int(expected)"
        )

        assert not result.success
        assert "SyntaxError" in result.message

    @pytest.mark.asyncio
    async def test_undefined_error(self, executor, undefined_variable_solution):
        result = await executor.execute_code(
            code=undefined_variable_solution,
            method_name="add",
            test_cases=["--arg1=1 --arg2=2", "--arg1=2 --arg2=2"],
            expected_results=["3", "4"],
            sample_test_cases=["--arg1=1 --arg2=2", "--arg1=0 --arg2=0", "--arg1=-1 --arg2=1"],
            sample_expected_results=["3", "0", "0"],
            difficulty="easy",
            compare_func="return result == int(expected)"
        )

        assert result.success
        assert len(result.test_results) == 2
        assert not all(test["passed"] for test in result.test_results)
        assert all("error" in test for test in result.test_results)

    @pytest.mark.asyncio
    async def test_timeout(self, executor, infinite_loop_solution):
        result = await executor.execute_code(
            code=infinite_loop_solution,
            method_name="add",
            test_cases=["--arg1=1 --arg2=2"],
            expected_results=["3"],
            sample_test_cases=["--arg1=1 --arg2=2", "--arg1=0 --arg2=0", "--arg1=-1 --arg2=1"],
            sample_expected_results=["3", "0", "0"],
            difficulty="easy",
            compare_func="return result == int(expected)"
        )

        assert not result.success
        assert "Time Limit Exceeded" in result.message

    @pytest.mark.asyncio
    async def test_memory_limit(self, executor, memory_heavy_solution):
        result = await executor.execute_code(
            code=memory_heavy_solution,
            method_name="add",
            test_cases=["--arg1=1 --arg2=2"],
            expected_results=["3"],
            sample_test_cases=["--arg1=1 --arg2=2", "--arg1=0 --arg2=0", "--arg1=-1 --arg2=1"],
            sample_expected_results=["3", "0", "0"],
            difficulty="easy",
            compare_func="return result == int(expected)"
        )

        assert not result.success
        assert "Memory Limit Exceeded" in result.message

    @pytest.mark.asyncio
    async def test_complex_problem(self, executor, valid_solution):
        result = await executor.execute_code(
            code=valid_solution,
            method_name="twoSum",
            test_cases=[
                "--arg1=[2,7,11,15] --arg2=9",
                "--arg1=[3,2,4] --arg2=6",
                "--arg1=[3,3] --arg2=6"
            ],
            expected_results=[
                "[0,1]",
                "[1,2]",
                "[0,1]"
            ],
            sample_test_cases=[
                "--arg1=[2,7,11,15] --arg2=9",
                "--arg1=[3,2,4] --arg2=6",
                "--arg1=[3,3] --arg2=6"
            ],
            sample_expected_results=[
                "[0,1]",
                "[1,2]",
                "[0,1]"
            ],
            difficulty="easy",
            compare_func="return sorted(result) == sorted(eval(expected))"
        )

        assert result.success
        assert len(result.test_results) == 3
        assert all(test["passed"] for test in result.test_results)

    @pytest.mark.asyncio
    async def test_concurrent_executions(self, executor, valid_solution):
        tasks = []
        for _ in range(20):
            tasks.append(
                executor.execute_code(
                    code=valid_solution,
                    method_name="add",
                    test_cases=["--arg1=1 --arg2=2"],
                    expected_results=["3"],
                    sample_test_cases=["--arg1=1 --arg2=2"],
                    sample_expected_results=["3"],
                    difficulty="hard",
                    compare_func="return result == int(expected)"
                )
            )

        results = await asyncio.gather(*tasks)
        assert all(r.success for r in results)
        assert len(results) == 20

    def test_different_difficulty_semaphores(self, executor):
        assert executor._execution_semaphores["easy"]._value > \
            executor._execution_semaphores["medium"]._value > \
            executor._execution_semaphores["hard"]._value

class TestJava:
    @pytest.fixture
    def executor(self):
        return CodeExecutionService()

    @pytest.fixture
    def valid_solution(self):
        return """
class Solution {
    public int add(int a, int b) {
        return a + b;
    }
    
    public int[] twoSum(int[] nums, int target) {
        Map<Integer, Integer> seen = new HashMap<>();
        for (int i = 0; i < nums.length; i++) {
            int complement = target - nums[i];
            if (seen.containsKey(complement)) {
                return new int[] {seen.get(complement), i};
            }
            seen.put(nums[i], i);
        }
        return new int[]{};
    }
}
"""

    @pytest.fixture
    def invalid_syntax_solution(self):
        return """
class Solution {
    public int add(int a, int b) {
        return a + b
    }
}
"""

    @pytest.fixture
    def undefined_variable_solution(self):
        return """
class Solution {
    public int add(int a, int b) {
        return n;
    }
}
"""

    @pytest.fixture
    def infinite_loop_solution(self):
        return """
class Solution {
    public int add(int a, int b) {
        while(true) {}
        return a + b;
    }
}
"""

    @pytest.fixture
    def memory_heavy_solution(self):
        return """
    class Solution {
        public int add(int a, int b) {
            List<Integer> x = new ArrayList<>();
            for (int i = 0; i < 10000000; i++) {
                x.add(i);
            }
            return a + b;
        }
    }
    """

    @pytest.mark.asyncio
    async def test_successful_execution(self, executor, valid_solution):
        result = await executor.execute_code(
            code=valid_solution,
            method_name="add",
            test_cases=["--arg1=1 --arg2=2", "--arg1=0 --arg2=0", "--arg1=-1 --arg2=1"],
            expected_results=["3", "0", "0"],
            sample_test_cases=["--arg1=1 --arg2=2", "--arg1=0 --arg2=0", "--arg1=-1 --arg2=1"],
            sample_expected_results=["3", "0", "0"],
            difficulty="easy",
            compare_func="return ((Integer)result).intValue() == ((Integer)expected).intValue();",
            lang="java"
        )

        assert result.success
        assert len(result.test_results) == 3
        assert all(test["passed"] for test in result.test_results)

    @pytest.mark.asyncio
    async def test_failed_test_cases(self, executor, valid_solution):
        result = await executor.execute_code(
            code=valid_solution,
            method_name="add",
            test_cases=["--arg1=1 --arg2=2", "--arg1=0 --arg2=0"],
            expected_results=["4", "1"],
            sample_test_cases=["--arg1=1 --arg2=2", "--arg1=0 --arg2=0"],
            sample_expected_results=["3", "0"],
            difficulty="easy",
            compare_func="return ((Integer)result).intValue() == ((Integer)expected).intValue();",
            lang="java"
        )

        assert result.success
        assert len(result.test_results) == 2
        assert not any(test["passed"] for test in result.test_results)
        assert all("error" not in test for test in result.test_results)

    @pytest.mark.asyncio
    async def test_syntax_error(self, executor, invalid_syntax_solution):
        result = await executor.execute_code(
            code=invalid_syntax_solution,
            method_name="add",
            test_cases=["--arg1=1 --arg2=2"],
            expected_results=["3"],
            sample_test_cases=["--arg1=1 --arg2=2"],
            sample_expected_results=["3"],
            difficulty="easy",
            compare_func="return ((Integer)result).intValue() == ((Integer)expected).intValue();",
            lang="java"
        )

        assert not result.success
        assert "error" in result.message.lower()

    @pytest.mark.asyncio
    async def test_undefined_error(self, executor, undefined_variable_solution):
        result = await executor.execute_code(
            code=undefined_variable_solution,
            method_name="add",
            test_cases=["--arg1=1 --arg2=2"],
            expected_results=["3"],
            sample_test_cases=["--arg1=1 --arg2=2"],
            sample_expected_results=["3"],
            difficulty="easy",
            compare_func="return ((Integer)result).intValue() == ((Integer)expected).intValue();",
            lang="java"
        )

        assert not result.success
        assert "error" in result.message.lower()

    @pytest.mark.asyncio
    async def test_timeout(self, executor, infinite_loop_solution):
        result = await executor.execute_code(
            code=infinite_loop_solution,
            method_name="add",
            test_cases=["--arg1=1 --arg2=2"],
            expected_results=["3"],
            sample_test_cases=["--arg1=1 --arg2=2"],
            sample_expected_results=["3"],
            difficulty="easy",
            compare_func="return ((Integer)result).intValue() == ((Integer)expected).intValue();",
            lang="java"
        )

        assert not result.success
        assert "error" in result.message.lower()

    @pytest.mark.asyncio
    async def test_memory_limit(self, executor, memory_heavy_solution):
        result = await executor.execute_code(
            code=memory_heavy_solution,
            method_name="add",
            test_cases=["--arg1=1 --arg2=2"],
            expected_results=["3"],
            sample_test_cases=["--arg1=1 --arg2=2"],
            sample_expected_results=["3"],
            difficulty="easy",
            compare_func="return ((Integer)result).intValue() == ((Integer)expected).intValue();",
            lang="java"
        )

        assert all("error" in test for test in result.test_results)

    @pytest.mark.asyncio
    async def test_complex_problem(self, executor, valid_solution):
        result = await executor.execute_code(
            code=valid_solution,
            method_name="twoSum",
            test_cases=[
                "--arg1=[2,7,11,15] --arg2=9",
                "--arg1=[3,2,4] --arg2=6",
                "--arg1=[3,3] --arg2=6"
            ],
            expected_results=[
                "[0,1]",
                "[1,2]",
                "[0,1]"
            ],
            sample_test_cases=[
                "--arg1=[2,7,11,15] --arg2=9",
                "--arg1=[3,2,4] --arg2=6",
                "--arg1=[3,3] --arg2=6"
            ],
            sample_expected_results=[
                "[0,1]",
                "[1,2]",
                "[0,1]"
            ],
            difficulty="easy",
            compare_func="return Arrays.equals((int[]) result, (int[]) expected);",
            lang="java"
        )

        assert result.success
        assert len(result.test_results) == 3
        assert all(test["passed"] for test in result.test_results)

    @pytest.mark.asyncio
    async def test_concurrent_executions(self, executor, valid_solution):
        tasks = []
        for _ in range(20):
            tasks.append(
                executor.execute_code(
                    code=valid_solution,
                    method_name="add",
                    test_cases=["--arg1=1 --arg2=2"],
                    expected_results=["3"],
                    sample_test_cases=["--arg1=1 --arg2=2"],
                    sample_expected_results=["3"],
                    difficulty="hard",
                    compare_func="return ((Integer)result).intValue() == ((Integer)expected).intValue();",
                    lang="java"
                )
            )

        results = await asyncio.gather(*tasks)
        assert all(r.success for r in results)
        assert len(results) == 20
    
    def test_different_difficulty_semaphores(self, executor):
        assert executor._execution_semaphores["easy"]._value > \
            executor._execution_semaphores["medium"]._value > \
            executor._execution_semaphores["hard"]._value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
