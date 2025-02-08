PYTHON_TEMPLATE = r"""{code}

import json
import traceback
from typing import *

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
            "passed_tests": len([r for r in results if r["passed"]),
        }}
    }}
    
if __name__ == "__main__":
    test_data = {test_data}
    sample_data = {sample_data}
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

JAVA_TEMPLATE = r"""import org.junit.*;
import org.junit.runner.JUnitCore;
import com.google.gson.*;
import java.lang.reflect.*;

{code}

public class {file_name} {{
    private static JsonObject compareResults(Object result, String expected) {{
        JsonObject comparison = new JsonObject();
        comparison.addProperty("passed", result.toString().equals(expected));
        return comparison;
    }}

    public static JsonArray runTests(Solution solution, JsonArray testData) {{
        JsonArray results = new JsonArray();
        Gson gson = new Gson();
        
        for (JsonElement testElement : testData) {{
            JsonObject test = testElement.getAsJsonObject();
            JsonObject result = new JsonObject();
            
            try {{
                String inputStr = test.get("input").getAsString();
                Class<?>[] paramTypes = getParameterTypes(inputStr);
                Object[] args = parseArguments(inputStr);
                
                // Replace "maxProfit" with the method you want to test if needed.
                Method method = Solution.class.getMethod("maxProfit", paramTypes);
                Object output = method.invoke(solution, args);
                JsonObject comparison = compareResults(output, test.get("expected").getAsString());
                result.addProperty("passed", comparison.get("passed").getAsBoolean());
                result.addProperty("output", gson.toJson(output));
            }} catch (Exception e) {{
                result.addProperty("error", e.toString());
                result.addProperty("passed", false);
            }}
            results.add(result);
        }}
        return results;
    }}

    private static Class<?>[] getParameterTypes(String input) {{
        return new Class<?>[] {{ int[].class }};
    }}

    private static Object[] parseArguments(String input) {{
        int startBracket = input.indexOf('[');
        int endBracket = input.lastIndexOf(']');
        if (startBracket != -1 && endBracket != -1) {{
            String[] numStrs = input.substring(startBracket + 1, endBracket).split(",");
            int[] nums = new int[numStrs.length];
            for (int i = 0; i < numStrs.length; i++) {{
                nums[i] = Integer.parseInt(numStrs[i].trim());
            }}
            return new Object[] {{ nums }};
        }}
        return new Object[0];
    }}

    // This method now wraps the results in a "test_results" field and adds a "summary" field.
    private static JsonObject createResultObject(JsonArray results) {{
        JsonObject summary = new JsonObject();
        int totalTests = results.size();
        int passedTests = 0;
        for (JsonElement element : results) {{
            JsonObject res = element.getAsJsonObject();
            if (res.has("passed") && res.get("passed").getAsBoolean()) {{
                passedTests++;
            }}
        }}
        summary.addProperty("total_tests", totalTests);
        summary.addProperty("passed_tests", passedTests);
        
        JsonObject obj = new JsonObject();
        obj.add("test_results", results);
        obj.add("summary", summary);
        return obj;
    }}

    public static void main(String[] args) {{
        try {{
            Gson gson = new Gson();
            Solution solution = new Solution();

            JsonArray testData = gson.fromJson("{test_data}", JsonArray.class);
            JsonArray sampleData = gson.fromJson("{sample_data}", JsonArray.class);

            JsonObject results = new JsonObject();
            results.add("hidden_results", createResultObject(runTests(solution, testData)));
            results.add("sample_results", createResultObject(runTests(solution, sampleData)));

            System.out.println("EXECUTION_RESULTS:" + results);
        }} catch (Exception e) {{
            System.out.println("GLOBAL_ERROR:\n" + e);
        }}
    }}
}}

"""

CPP_TEMPLATE = r"""{code}

\#include <iostream>
\#include <vector>
\#include <sstream>
\#include <json/json.h>

Json::Value compareResults(auto result, const std::string& expected) {{
    {compare_func}
}}

Json::Value runTests(Solution& solution, const Json::Value& testData) {{
    Json::Value results(Json::arrayValue);
    
    for (const auto& test : testData) {{
        Json::Value result;
        try {{
            std::istringstream iss(test["input"].asString());
            // Parameter parsing logic
            auto output = solution.{method_name}(/* parsed args */);
            Json::Value comparison = compareResults(output, test["expected"].asString());
            result["passed"] = comparison["passed"];
            result["output"] = Json::Value(output);
        }} catch (const std::exception& e) {{
            result["error"] = e.what();
            result["passed"] = false;
        }}
        results.append(result);
    }}
    return results;
}}

int main() {{
    Solution solution;
    Json::Reader reader;
    Json::Value testData, sampleData;
    
    reader.parse("{test_data}", testData);
    reader.parse("{sample_data}", sampleData);
    
    Json::Value results;
    results["hidden_results"] = runTests(solution, testData);
    results["sample_results"] = runTests(solution, sampleData);
    
    std::cout << "EXECUTION_RESULTS:" << results.toStyledString();
    return 0;
}}
"""
