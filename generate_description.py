import json
from openai import OpenAI


def main():
    # Get API key from input (passed as an argument)
    import sys

    api_key = sys.argv[1]

    # Initialize the OpenAI client
    client = OpenAI(api_key=api_key)

    # Read the content of the diff file
    with open("diff.txt", "r") as file:
        diff_content = file.read()

    content = (
        f"Provide a PR description (be elaborate and have bullet points or an itemized "
        f"list for the changes made) as JSON with keys 'title' (value is string markdown) "
        f"and 'description' (value is string in markdown), given this diff:\n"
        f"{diff_content}."
    )

    # Generate the completion
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "user", "content": content},
        ],
    )

    # Get the response and parse it
    result = completion.choices[0].message.content
    result_dictionary = json.loads(result)

    # Write the response to a file
    with open("description.txt", "w") as file:
        file.write(result_dictionary["description"])

    with open("title.txt", "w") as file:
        file.write(result_dictionary["title"])


if __name__ == "__main__":
    main()
