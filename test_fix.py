#!/usr/bin/env python3

"""
Simple test to verify the TestResult.to_dict() fix
This test runs independently without requiring environment setup
"""

import sys
import os

# Add the app directory to the path so we can import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.execution.types import TestResult

def test_to_dict_fix():
    """Test that TestResult.to_dict() returns proper dict structure"""
    
    # Create a test result with output and error
    test_result = TestResult(
        expected="hello",
        passed=False,
        output="world", 
        logs="some logs",
        error="syntax error",
        input="test input"
    )
    
    # Call to_dict() - this should not crash and should return proper structure
    result_dict = test_result.to_dict(is_sample=True)
    
    # Verify the structure is correct
    assert isinstance(result_dict, dict), "Result should be a dictionary"
    assert "expected" in result_dict, "Should contain 'expected' key"
    assert "output" in result_dict, "Should contain 'output' key"
    assert "passed" in result_dict, "Should contain 'passed' key"
    assert "error" in result_dict, "Should contain 'error' key"
    assert "logs" in result_dict, "Should contain 'logs' key for sample"
    assert "input" in result_dict, "Should contain 'input' key for sample"
    
    # Verify the values are correct
    assert result_dict["expected"] == "hello"
    assert result_dict["output"] == "world"
    assert result_dict["passed"] == False
    assert result_dict["error"] == "syntax error"
    assert result_dict["logs"] == "some logs"
    assert result_dict["input"] == "test input"
    
    print("✅ TestResult.to_dict() is working correctly!")
    
    # Test with is_sample=False
    result_dict_no_sample = test_result.to_dict(is_sample=False)
    assert "logs" not in result_dict_no_sample, "Should not contain 'logs' when is_sample=False"
    assert "input" not in result_dict_no_sample, "Should not contain 'input' when is_sample=False"
    
    print("✅ TestResult.to_dict(is_sample=False) is working correctly!")

if __name__ == "__main__":
    test_to_dict_fix()
    print("🎉 All tests passed! The bug fix is working.")