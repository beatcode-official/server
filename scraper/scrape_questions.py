import json
import leetscrape
from tqdm import tqdm


def main():
    ls = leetscrape.GetQuestionsList()
    ls.scrape()

    df = ls.questions

    fetchLimit = 50

    filtered = df[
        (df['difficulty'] == 'Easy')
        & (df['paidOnly'] == False)
        & (df['acceptanceRate'] < 60)
        & (df['acceptanceRate'] > 40)
    ][:fetchLimit]

    result = []

    for _, row in tqdm(filtered.iterrows(), total=fetchLimit):
        question = leetscrape.GetQuestion(row['titleSlug']).scrape()
        signature = question.Code

        # Ignore first line and outdent the code by 1 level
        signature = "\n".join(signature.split("\n")[1:])
        signature = "\n".join([line[4:] for line in signature.split("\n")])

        questionObj = {
            "id": len(result),
            "title": question.title,
            "description": question.Body,
            "signature": signature,
            "test_cases": [],
            "expected_outputs": [],
            "compare_func": "",
        }

        result.append(questionObj)

    """
    database.json
    {
        "CHALLENGES": result   
    }
    """
    with open("raw_database.json", "w") as f:
        json.dump({"CHALLENGES": result}, f, indent=4)


if __name__ == '__main__':
    main()
