PYTHON_TEMPLATE = r"""import json
import traceback
from typing import *

{code}

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
    
def compare_results(result: Any, expected: str) -> bool:
    {compare_func}

def format_test_data(method_name: str, args: str) -> str:
    arg_list = args.split("--arg")
    arg_list = [a.strip() for a in arg_list if a.strip()]
    params = []
    for arg in arg_list:
        if "=" in arg:
            _, val = arg.split("=", 1)
            params.append(val.strip())
    return f"{{method_name}}({{', '.join(params)}})"

def run_tests(solution, method_name, test_data, is_sample: bool = False):
    results = []
    
    for test in test_data:
        try:
            result = eval(f"solution.{{format_test_data(method_name, test['input'])}}")
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
    method_name = {method_name!r}
    test_data = {test_data}
    sample_data = {sample_data}

    solution = Solution()
    hidden_results = run_tests(solution, method_name, test_data, is_sample=False)
    sample_results = run_tests(solution, method_name, sample_data, is_sample=True)
    results = {{
        "hidden_results": hidden_results,
        "sample_results": sample_results
    }}
    with open("{file_name}-results.txt", "w") as f:
        f.write(json.dumps(results))
"""

JAVA_TEMPLATE = r"""
import org.junit.*;
import org.junit.runner.JUnitCore;
import com.google.gson.*;
import java.lang.reflect.*;
import java.util.*;

{code}

public class {file_name} {{
    private static class Unknown {{
        private final String value;

        public Unknown(String value) {{
            this.value = value;
        }}

        public String get() {{
            return value;
        }}

        @Override
        public String toString() {{
            return value;
        }}
    }}

    private static boolean compare(Object result, Object expected) {{
        {compare_func}
    }}

    public static JsonArray runTests(Solution solution, JsonArray testData) {{
        JsonArray results = new JsonArray();
        Gson gson = new Gson();

        Method[] methods = Solution.class.getMethods();
        Method targetMethod = null;

        for (Method method : methods) {{
            if (method.getName().equals("{method_name}")) {{
                if (targetMethod == null) {{
                    targetMethod = method;
                }} else {{
                    throw new RuntimeException("Multiple '{method_name}' methods found. Cannot determine which to use.");
                }}
            }}
        }}

        if (targetMethod == null) {{
            throw new RuntimeException("Method '{method_name}' not found.");
        }}

        Class<?>[] paramTypes = targetMethod.getParameterTypes();
        Class<?> returnType = targetMethod.getReturnType();

        for (JsonElement testElement : testData) {{
            JsonObject test = testElement.getAsJsonObject();
            JsonObject result = new JsonObject();

            try {{
                String inputStr = test.get("input").getAsString();
                Object[] args = parseArguments(inputStr, paramTypes);
                Object output = targetMethod.invoke(solution, args);
                Object expected = parseValue(test.get("expected").getAsString(), returnType);

                boolean passed = compare(output, expected);
                result.addProperty("passed", passed);
                result.addProperty("output", gson.toJson(output));
                result.addProperty("expected", test.get("expected").getAsString());
            }} catch (Exception e) {{
                Throwable cause = e;
                if (e instanceof InvocationTargetException && e.getCause() != null) {{
                    cause = e.getCause();
                }}
                result.addProperty("error", cause.toString());
                result.addProperty("passed", false);
            }}
            results.add(result);
        }}
        return results;
    }}


    private static Object parsePrimitiveArray(String arrayContent, Class<?> componentType) {{
        if (arrayContent.trim().isEmpty()) {{
            return Array.newInstance(componentType, 0);
        }}

        String[] elements = arrayContent.split("\\s*,\\s*");
        Object array = Array.newInstance(componentType, elements.length);

        for (int i = 0; i < elements.length; i++) {{
            String element = elements[i].trim();
            if (componentType == int.class) {{
                Array.setInt(array, i, Integer.parseInt(element));
            }} else if (componentType == long.class) {{
                Array.setLong(array, i, Long.parseLong(element));
            }} else if (componentType == double.class) {{
                Array.setDouble(array, i, Double.parseDouble(element));
            }} else if (componentType == float.class) {{
                Array.setFloat(array, i, Float.parseFloat(element));
            }} else if (componentType == boolean.class) {{
                Array.setBoolean(array, i, Boolean.parseBoolean(element));
            }} else if (componentType == byte.class) {{
                Array.setByte(array, i, Byte.parseByte(element));
            }} else if (componentType == short.class) {{
                Array.setShort(array, i, Short.parseShort(element));
            }} else if (componentType == char.class) {{
                Array.setChar(array, i, element.charAt(0));
            }} else {{
                throw new IllegalArgumentException("Unsupported primitive type: " + componentType);
            }}
        }}
        return array;
    }}

    private static Object parseValue(String value, Class<?> targetType) {{
        if (value == null || value.trim().equals("null")) {{
            return null;
        }}

        value = value.trim();

        // Handle unknown
        if (targetType == Unknown.class) {{
            return new Unknown(value);
        }}

        // Handle arrays
        if (targetType.isArray()) {{
            if (!value.startsWith("[") || !value.endsWith("]")) {{
                throw new IllegalArgumentException("Expected array value, got: " + value);
            }}

            String arrayContent = value.substring(1, value.length() - 1);
            Class<?> componentType = targetType.getComponentType();

            if (componentType.isPrimitive()) {{
                return parsePrimitiveArray(arrayContent, componentType);
            }} else {{
                Object[] parsed = parseArray(arrayContent, componentType);
                Object typedArray = Array.newInstance(componentType, parsed.length);
                System.arraycopy(parsed, 0, typedArray, 0, parsed.length);
                return typedArray;
            }}
        }}

        // Handle strings
        if (targetType == String.class) {{
            if ((value.startsWith("\"") && value.endsWith("\"")) || 
                (value.startsWith("'") && value.endsWith("'"))) {{
                return value.substring(1, value.length() - 1);
            }}
            return value;
        }}

        // Handle List type
        if (List.class.isAssignableFrom(targetType)) {{
            if (!value.startsWith("[") || !value.endsWith("]")) {{
                throw new IllegalArgumentException("Expected list value, got: " + value);
            }}
            // Parse the content within the brackets recursively 
            // Passing String.class so that nested lists are also parsed correctly.
            Object[] parsed = parseArray(value.substring(1, value.length() - 1), Unknown.class);
            List<Object> list = new ArrayList<>();
            for (Object item : parsed) {{
                if (item instanceof Unknown) {{
                    list.add(parseValueWithoutType(item.toString()));
                }} else {{
                    list.add(item);
                }}
            }}
            return list;
        }}

        // Handle primitive types and their wrappers
        if (targetType == boolean.class || targetType == Boolean.class) {{
            return Boolean.parseBoolean(value);
        }}
        if (targetType == int.class || targetType == Integer.class) {{
            return Integer.parseInt(value);
        }}
        if (targetType == long.class || targetType == Long.class) {{
            return Long.parseLong(value);
        }}
        if (targetType == double.class || targetType == Double.class) {{
            return Double.parseDouble(value);
        }}
        if (targetType == float.class || targetType == Float.class) {{
            return Float.parseFloat(value);
        }}
        if (targetType == byte.class || targetType == Byte.class) {{
            return Byte.parseByte(value);
        }}
        if (targetType == short.class || targetType == Short.class) {{
            return Short.parseShort(value);
        }}
        if (targetType == char.class || targetType == Character.class) {{
            String trimmed = value.trim().substring(1, value.length() - 1);
            if (trimmed.length() != 1) {{
                throw new IllegalArgumentException("Cannot convert to char: " + value);
            }}
            return trimmed.charAt(0);
        }}

        throw new IllegalArgumentException("Unsupported type: " + targetType.getName());
    }}

    // Bad code alert
    private static Object parseValueWithoutType(String value) {{
        value = value.trim();

        if (value.startsWith("[") && value.endsWith("]")) {{
            return parseValue(value, List.class);
        }} else if (value.startsWith("\"") && value.endsWith("\"") || value.startsWith("'") && value.endsWith("'")) {{
            return parseValue(value, String.class);
        }} else if (value.equalsIgnoreCase("true") || value.equalsIgnoreCase("false")) {{
            return parseValue(value, Boolean.class);
        }} else if (value.matches("-?\\d+(\\.\\d+)?")) {{
            if (value.contains(".")) {{
                try {{
                    return parseValue(value, Double.class);
                }} catch (IllegalArgumentException ex) {{
                    return parseValue(value, Float.class);
                }}
            }}
            try {{
                return parseValue(value, Integer.class);
            }} catch (IllegalArgumentException ex) {{
                return parseValue(value, Long.class);
            }}
        }}
        return value;
    }}

    private static Object[] parseArguments(String input, Class<?>[] paramTypes) {{
        List<Object> arguments = new ArrayList<>();
        String[] parts = input.split("--arg\\d+");
        int argIndex = 0;

        for (String part : parts) {{
            if (part.trim().isEmpty()) continue;

            String value = part.trim();
            if (value.startsWith("=")) {{
                value = value.substring(1).trim();
            }}

            if (argIndex >= paramTypes.length) {{
                throw new IllegalArgumentException("More arguments provided than parameter types");
            }}

            arguments.add(parseValue(value, paramTypes[argIndex]));
            argIndex++;
        }}

        if (argIndex != paramTypes.length) {{
            throw new IllegalArgumentException("Not enough arguments provided for parameter types");
        }}

        return arguments.toArray();
    }}

    private static Object[] parseArray(String arrayContent, Class<?> componentType) {{
        List<Object> elements = new ArrayList<>();
        if (arrayContent.trim().isEmpty()) {{
            return (Object[]) Array.newInstance(componentType, 0);
        }}

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
            }} else if (c == ',' && depth == 0) {{
                if (inString) {{
                    elements.add(current.toString().substring(1, current.length() - 1));
                }} else {{
                    elements.add(parseValue(current.toString().trim(), componentType));
                }}
                current.setLength(0);
            }} else {{
                current.append(c);
            }}
        }}

        if (current.length() > 0) {{
            elements.add(parseValue(current.toString().trim(), componentType));
        }}

        Object[] result = (Object[]) Array.newInstance(componentType, elements.size());
        return elements.toArray(result);
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

            String testStr = {test_data};
            String sampleStr = {sample_data};
            JsonArray testData = gson.fromJson(testStr, JsonArray.class);
            JsonArray sampleData = gson.fromJson(sampleStr, JsonArray.class);

            JsonObject results = new JsonObject();
            results.add("hidden_results", createResultObject(runTests(solution, testData)));
            results.add("sample_results", createResultObject(runTests(solution, sampleData)));

            java.io.FileWriter file = new java.io.FileWriter("{file_name}-results.txt");
            file.write(results.toString());
            file.close();
        }} catch (Exception e) {{
            Throwable cause = e;
            if (e instanceof InvocationTargetException && e.getCause() != null) {{
                cause = e.getCause();
            }}
            throw new RuntimeException(cause);
        }}
    }}
}}
"""


CPP_TEMPLATE = r"""#include <fstream>
#include <functional>
#include <iostream>
#include <json/json.h>
#include <regex>
#include <sstream>
#include <tuple>
#include <type_traits>
#include <bits/stdc++.h>
#include <vector>

using namespace std;

{code}

template <typename T> struct function_traits;
template <typename> struct always_false : std::false_type {{}};
template <typename> struct is_vector : std::false_type {{}};
template <typename T> struct is_vector<std::vector<T>> : std::true_type {{}};

template <typename C, typename R, typename... Args>
struct function_traits<R (C::*)(Args...)> {{
    using return_type = R;
    using args_tuple = std::tuple<typename std::remove_reference<Args>::type...>;
    static constexpr size_t arg_count = sizeof...(Args);
}};

template <size_t N, typename T>
using tuple_element_t = typename std::tuple_element<N, T>::type;
template <size_t N, typename T> struct arg_type {{
  using type = std::tuple_element_t<N, typename function_traits<T>::args_tuple>;
}};

template <typename T> T jsonToValue(const Json::Value &val) {{
    // Handle nested vectors recursively
    if constexpr (is_vector<T>::value) {{
        using ElementType = typename T::value_type;
        T result;
        for (const auto &elem : val) {{
            result.push_back(jsonToValue<ElementType>(elem));
        }}
        return result;
    }}
    // Handle chars specifically
    else if constexpr (std::is_same_v<T, char>) {{
        if (val.isString()) {{
            std::string str_val = val.asString();
            if (!str_val.empty()) {{
                return str_val[0];
            }} else {{
                throw std::runtime_error("JSON string for char is empty");
            }}
        }} else {{
            throw std::runtime_error("JSON value for char is not a string");
        }}
    }}
    // Handle arithmetic types (int, float, double)
    else if constexpr (std::is_arithmetic_v<T>) {{
        if (val.isNumeric()) {{
            return static_cast<T>(val.isDouble() ? val.asDouble() : val.asInt());
        }}
        throw std::runtime_error("JSON value is not numeric");
    }}
    // Handle strings
    else if constexpr (std::is_same_v<T, std::string>) {{
        return val.asString();
    }}
    else {{
        static_assert(always_false<T>::value, "Unsupported type for JSON parsing");
    }}
}}

template <typename T> Json::Value valueToJson(const T &value) {{
    // Handle vectors recursively
    if constexpr (is_vector<T>::value) {{
        Json::Value json_array(Json::arrayValue);
        for (const auto &elem : value) {{
            json_array.append(valueToJson(elem));
        }}
        return json_array;
    }}
    // Handle arithmetic types
    else if constexpr (std::is_arithmetic_v<T>) {{
        return Json::Value(value);
    }}
    // Handle strings
    else if constexpr (std::is_same_v<T, std::string>) {{
        return Json::Value(value);
    }} else {{
        static_assert(always_false<T>::value, "Unsupported type for JSON serialization");
    }}
}}

struct ArgType {{
    Json::Value data;
    std::function<void *(void)> converter;

    template <typename T> T get() const {{ return jsonToValue<T>(data); }}
}};

vector<ArgType> parseArguments(const string& input) {{
    vector<ArgType> args;
    istringstream iss(input);
    string token;
    Json::CharReaderBuilder builder;
    Json::CharReader* reader = builder.newCharReader();
    string errors;

    while (iss >> token) {{
        size_t eq_pos = token.find('=');
        if (eq_pos == std::string::npos || token.find("--arg") != 0)
            continue;

        std::string value_str = token.substr(eq_pos + 1);
        Json::Value json_val;

        // Attempt to parse as JSON
        if (reader->parse(value_str.c_str(), value_str.c_str() + value_str.length(), &json_val, &errors)) {{
            args.push_back({{json_val}});
        }} else {{
            // If not valid JSON, treat as string (highly likely with single quotes)
            if (value_str.front() == '\'' && value_str.back() == '\'') {{
                args.push_back({{Json::Value(value_str.substr(1, value_str.length() - 2))}});
            }} else {{
                args.push_back({{Json::Value(value_str)}});
            }}
        }}
    }}
    delete reader;
    return args;
}}

bool compare(const Json::Value &result, const Json::Value &expected) {{
    {compare_func}
}}

Json::Value runTests(Solution& solution, const Json::Value& testData) {{
    Json::Value results(Json::arrayValue);
    Json::CharReaderBuilder builder;
    Json::CharReader* reader = builder.newCharReader();
    string errors;

    for (const auto &test : testData) {{
        Json::Value testResult;
        try {{
            auto args = parseArguments(test["input"].asString());

            using Solution_t = decltype(Solution());
            using Method_t = decltype(&Solution_t::{method_name});

            {args_init}
            auto output = solution.{method_name}({args_param});

            Json::Value expected;
            reader->parse(test["expected"].asString().c_str(),
                        test["expected"].asString().c_str() +
                        test["expected"].asString().length(),
                    &expected, &errors);

            Json::Value output_json= valueToJson(output);

            testResult["passed"] = compare(output_json, expected);
            Json::StreamWriterBuilder writer;
            writer["indentation"] = "";
            testResult["output"] = Json::writeString(writer, output_json);
            testResult["expected"] = Json::writeString(writer, expected);

        }} catch (const exception &e) {{
            testResult["error"] = e.what();
            testResult["passed"] = false;
        }}
        results.append(testResult);
    }}
    delete reader;
    return results;
}}

Json::Value formatResults(const Json::Value& results) {{
    Json::Value formatted;
    int total_tests = results.size();
    int passed_tests = 0;
    
    for (const auto& test : results) {{
        if (test["passed"].asBool()) {{
            passed_tests++;
        }}
    }}
    
    formatted["test_results"] = results;
    formatted["summary"]["total_tests"] = total_tests;
    formatted["summary"]["passed_tests"] = passed_tests;
    
    return formatted;
}}

int main() {{
    Solution solution;
    Json::CharReaderBuilder builder;
    Json::CharReader* reader = builder.newCharReader();
    Json::Value test_data, sample_data;
    string errors;
    
    const string test_str = "{test_data}";
    reader->parse(test_str.c_str(), test_str.c_str() + test_str.length(), &test_data, &errors);
    const string sample_str = "{sample_data}";
    reader->parse(sample_str.c_str(), sample_str.c_str() + sample_str.length(), &sample_data, &errors);
    delete reader;
    
    Json::Value results;
    results["hidden_results"] = formatResults(runTests(solution, test_data));
    results["sample_results"] = formatResults(runTests(solution, sample_data));
    
    ofstream output_file("{file_name}-results.txt");
    output_file << results.toStyledString() << endl;
    output_file.close();
    return 0;
}}
"""
