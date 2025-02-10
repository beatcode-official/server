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
    test_data = {test_data}
    method_name = {method_name!r}
    sample_data = {sample_data}

    try:
        solution = Solution()
        hidden_results = run_tests(solution, method_name, test_data, is_sample=False)
        sample_results = run_tests(solution, method_name, sample_data, is_sample=True)
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
    private static boolean compare(Object result, Object expected) {{
        {compare_func}
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
                boolean passed = compare(output, parseValue(test.get("expected").getAsString()));
                result.addProperty("passed", passed);
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

    private static Object[] parseArray(String arrayContent) {{
        List<Object> elements = new ArrayList<>();
        if (arrayContent.trim().isEmpty()) {{
            return new Object[0];
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
            }} else if (!inString && c == ',' && depth == 0) {{
                elements.add(parseValue(current.toString().trim()));
                current.setLength(0); // reset the StringBuilder
            }} else {{
                current.append(c);
            }}
        }}

        if (current.length() > 0) {{
            elements.add(parseValue(current.toString().trim()));
        }}

        return elements.toArray(new Object[0]);
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
            Object[] elements = parseArray(value.substring(1, value.length() - 1));
            if (elements.length == 0) return elements;
            
            // Check if all elements are arrays
            boolean allArrays = Arrays.stream(elements)
                .allMatch(e -> e != null && e.getClass().isArray());
            if (allArrays) {{
                return elements;
            }}
            
            // Check if all elements are integers
            boolean allIntegers = Arrays.stream(elements)
                .allMatch(e -> e instanceof Integer);
            if (allIntegers) {{
                int[] result = new int[elements.length];
                for (int i = 0; i < elements.length; i++) {{
                    result[i] = (Integer)elements[i];
                }}
                return result;
            }}
            
            return elements;
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
            Throwable cause = e;
            if (e instanceof InvocationTargetException && e.getCause() != null) {{
                cause = e.getCause();
            }}
            System.out.println("GLOBAL_ERROR:\n" + cause.toString());
        }}
    }}
}}
"""


CPP_TEMPLATE = r"""#include <functional>
#include <iostream>
#include <json/json.h>
#include <regex>
#include <sstream>
#include <tuple>
#include <type_traits>
#include <vector>

template <typename T> struct function_traits;
template <typename> struct always_false : std::false_type {{}};
template <typename> struct is_vector : std::false_type {{}};
template <typename T> struct is_vector<std::vector<T>> : std::true_type {{}};

template <typename C, typename R, typename... Args>
struct function_traits<R (C::*)(Args...)> {{
    using return_type = R;
    using args_tuple = std::tuple<
        typename std::remove_reference<Args>::type...
    >;
    static constexpr size_t arg_count = sizeof...(Args);
}};

template <size_t N, typename T>
using tuple_element_t = typename std::tuple_element<N, T>::type;
template <size_t N, typename T> struct arg_type {{
  using type = tuple_element_t<N, typename function_traits<T>::args_tuple>;
}};

using namespace std;

{code}

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
            // If not valid JSON, treat as string
            args.push_back({{Json::Value(value_str)}});
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
    
    cout << "EXECUTION_RESULTS:" << results.toStyledString();
    return 0;
}}
"""
