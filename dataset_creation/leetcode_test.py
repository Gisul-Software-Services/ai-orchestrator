import requests

# ----------------------------
# CONFIG
# ----------------------------
DIFFICULTY = "EASY"   # EASY / MEDIUM / HARD
LIMIT = 10            # number of problems to fetch


# ----------------------------
# FETCH DATA FROM LEETCODE
# ----------------------------
def fetch_problems(difficulty, limit):
    url = "https://leetcode.com/graphql"

    query = """
    query getProblems($filters: QuestionListFilterInput) {
      questionList(categorySlug: "", limit: %d, skip: 0, filters: $filters) {
        data {
          title
          titleSlug
          difficulty
          topicTags {
            name
            slug
          }
        }
      }
    }
    """ % limit

    variables = {
        "filters": {
            "difficulty": difficulty
        }
    }

    headers = {
        "Content-Type": "application/json",
        "Referer": "https://leetcode.com"
    }

    res = requests.post(url, json={
        "query": query,
        "variables": variables
    }, headers=headers)

    return res.json()


# ----------------------------
# MAIN
# ----------------------------
if __name__ == "__main__":
    data = fetch_problems(DIFFICULTY, LIMIT)

    problems = data["data"]["questionList"]["data"]

    print("\n--- LeetCode Problems ---\n")

    for i, p in enumerate(problems, 1):
        tags = [t["slug"] for t in p["topicTags"]]

        print(f"{i}. {p['title']}")
        print(f"   Difficulty: {p['difficulty']}")
        print(f"   Tags: {tags}")
        print(f"   URL: https://leetcode.com/problems/{p['titleSlug']}/\n")
