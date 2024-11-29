import json
import os
import time
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_gpt4_response(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"An error occurred: {str(e)}"


def get_test_cases_and_outputs():
    with open("raw_database.json") as f:
        data = json.load(f)

    with open("prompt.txt", "r") as f:
        prompt = f.read()

    existing = False
    if os.path.exists("database.json"):
        with open("database.json", "r") as f:
            cur_db = json.load(f)["CHALLENGES"]
        existing = True

    new_db = {
        "CHALLENGES": []
    }

    for question in tqdm(data["CHALLENGES"][:1]):
        time.sleep(2)  # idk, please dont rate limit me openai

        # if the question is already in the current database, add the one in the current database to the new database
        if existing and any(q["id"] == question["id"] for q in cur_db):
            new_db["CHALLENGES"].append([q for q in cur_db if q["id"] == question["id"]][0])
            continue

        replaced_prompt = prompt.replace("|||AAA REPLACE THIS|||", json.dumps(question))

        response = get_gpt4_response(replaced_prompt)

        # take only the JSON part of the response
        stripped_response = response[response.index("{"):response.rindex("}") + 1].strip()

        parsed_response = json.loads(stripped_response)

        new_db["CHALLENGES"].append({
            "id": question["id"],
            "title": question["title"],
            "description": question["description"],
            "signature": question["signature"],
            "test_cases": parsed_response["test_cases"],
            "expected_outputs": parsed_response["expected_outputs"],
            "compare_func": parsed_response["compare_func"]
        })

        # write after every iteration to prevent data loss
        with open("database.json", "w") as f:
            json.dump(new_db, f, indent=4)


def main():
    get_test_cases_and_outputs()


if __name__ == '__main__':
    main()
