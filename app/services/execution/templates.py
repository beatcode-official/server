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
            "passed_tests": len([r for r in results if r["passed"]]),
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

JAVA_TEMPLATE = r"""
import org.junit.*;
import org.junit.runner.JUnitCore;
import com.google.gson.*;
import java.lang.reflect.*;
import java.util.*;

{code}

public class {file_name} {{
    private static JsonObject compareResults(Object result, Object expected) {{
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
                
                Method method = Solution.class.getMethod("{method_name}", paramTypes);
                Object output = method.invoke(solution, args);
                JsonObject comparison = compareResults(output, parseValue(test.get("expected").getAsString()); // bad code alert
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

    private static Class<?> getArrayType(Object arr) {{
        if (!arr.getClass().isArray()) {{
            return arr.getClass();
        }}
        
        Class<?> componentType = arr.getClass().getComponentType();
        if (componentType.isPrimitive()) {{
            return arr.getClass();
        }}
        
        Object[] array = (Object[]) arr;
        if (array.length == 0) {{
            return Object[].class;
        }}
        
        boolean allIntegers = true;
        boolean allArrays = true;
        
        for (Object element : array) {{
            if (element == null) continue;
            if (!(element instanceof Integer)) allIntegers = false;
            if (!element.getClass().isArray()) allArrays = false;
        }}
        
        if (allIntegers) return int[].class;
        if (allArrays) {{
            Object firstNonNull = null;
            for (Object element : array) {{
                if (element != null) {{
                    firstNonNull = element;
                    break;
                }}
            }}
            if (firstNonNull != null) {{
                Class<?> deeperType = getArrayType(firstNonNull);
                return Array.newInstance(deeperType.getComponentType(), 0).getClass();
            }}
        }}
        return Object[].class;
    }}

    private static Class<?>[] getParameterTypes(String input) {{
        Object[] args = parseArguments(input);
        Class<?>[] types = new Class<?>[args.length];
        for (int i = 0; i < args.length; i++) {{
            if (args[i] == null) {{
                types[i] = Object.class;
            }} else if (args[i].getClass().isArray()) {{
                types[i] = getArrayType(args[i]);
            }} else if (args[i] instanceof Integer || args[i] instanceof Long) {{
                types[i] = int.class;
            }} else if (args[i] instanceof Double || args[i] instanceof Float) {{
                types[i] = double.class;
            }} else if (args[i] instanceof Boolean) {{
                types[i] = boolean.class;
            }} else if (args[i] instanceof Character) {{
                types[i] = char.class;
            }} else {{
                types[i] = args[i].getClass();
            }}
        }}
        return types;
    }}

    private static Object[] parseArguments(String input) {{
        List<Object> arguments = new ArrayList<>();
        String[] parts = input.split("--arg\\d+");

        for (String part : parts) {{
            if (part.trim().isEmpty()) continue;

            String value = part.trim();
            if (value.startsWith("=")) {{
                value = value.substring(1).trim();
            }}

            arguments.add(parseValue(value));
        }}

        return arguments.toArray();
    }}

    private static List<Object> parseArray(String arrayContent) {{
        List<Object> elements = new ArrayList<>();
        if (arrayContent.trim().isEmpty()) return elements;
        
        StringBuilder current = new StringBuilder();
        int depth = 0;
        boolean inString = false;
        char stringChar = 0;

        for (char c : arrayContent.toCharArray()) {{
            if (c == '"' || c == '\'') {{
                if (!inString) {{
                    inString = true;
                    stringChar = c;
                }} else if (c == stringChar) {{
                    inString = false;
                }}
                current.append(c);
            }} else if (!inString && (c == '[' || c == '{{')) {{
                depth++;
                current.append(c);
            }} else if (!inString && (c == ']' || c == '}}')) {{
                depth--;
                current.append(c);
            }} else if (!inString && c == ',' && depth == 0) {{
                elements.add(parseValue(current.toString().trim()));
                current = new StringBuilder();
            }} else {{
                current.append(c);
            }}
        }}

        if (current.length() > 0) {{
            elements.add(parseValue(current.toString().trim()));
        }}

        return elements;
    }}

    private static Object parseValue(String value) {{
        value = value.trim();

        // Keep quoted strings as is
        if ((value.startsWith("'") && value.endsWith("'")) ||
            (value.startsWith("\"") && value.endsWith("\""))) {{
            return value.substring(1, value.length() - 1);
        }}

        // Handle null
        if (value.equals("null")) {{
            return null;
        }}

        // Handle boolean
        if (value.equals("true") || value.equals("false")) {{
            return Boolean.parseBoolean(value);
        }}

        // Handle arrays
        if (value.startsWith("[") && value.endsWith("]")) {{
            List<Object> elements = parseArray(value.substring(1, value.length() - 1));
            if (elements.isEmpty()) return new Object[0];
            
            // Check if all elements are arrays
            boolean allArrays = elements.stream()
                .allMatch(e -> e != null && e.getClass().isArray());
            if (allArrays) {{
                return elements.toArray();
            }}
            
            // Check if all elements are integers
            boolean allIntegers = elements.stream()
                .allMatch(e -> e instanceof Integer);
            if (allIntegers) {{
                int[] result = new int[elements.size()];
                for (int i = 0; i < elements.size(); i++) {{
                    result[i] = (Integer)elements.get(i);
                }}
                return result;
            }}
            
            return elements.toArray();
        }}

        // Handle objects/maps
        if (value.startsWith("{{") && value.endsWith("}}")) {{
            Map<String, Object> map = new HashMap<>();
            // TODO: Implement object parsing if needed
            return map;
        }}

        // Handle numbers
        try {{
            if (value.contains(".")) {{
                return Double.parseDouble(value);
            }}
            return Integer.parseInt(value);
        }} catch (NumberFormatException e) {{
            // If not a number, return as string
            return value;
        }}
    }}

    // Wraps the results in a "test_results" field and adds a "summary" field.
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
