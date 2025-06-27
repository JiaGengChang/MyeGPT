import os
import re
import requests
from dotenv import load_dotenv
assert load_dotenv('.env')
from langsmith import Client
from openevals.llm import create_llm_as_judge
from openevals.prompts import CORRECTNESS_PROMPT

# Define the input and reference output pairs that you'll use to evaluate your app
client = Client()

# Application logic
def target(inputs: dict) -> dict:
    response = requests.post(
        os.environ.get("APPLICATION_API_URL"),
        headers={"Content-Type": "application/json"},
        json={"user_input": inputs["question"]}
    )
    answer = response.json().get("response", "No response from API")
    # Remove HTML tags
    clean_answer = re.sub(r'<.*?>', '', answer)
    return {"answer": clean_answer}


# Define an LLM as a judge evaluator to evaluate correctness of the output
# Import a prebuilt evaluator prompt from openevals (https://github.com/langchain-ai/openevals) and create an evaluator.
def correctness_evaluator(inputs: dict, outputs: dict, reference_outputs: dict):
    evaluator = create_llm_as_judge(
        prompt=CORRECTNESS_PROMPT,
        model="openai:o4-mini",
        feedback_key="correctness",
    )
    eval_result = evaluator(
        inputs=inputs,
        outputs=outputs,
        reference_outputs=reference_outputs
    )
    return eval_result

if __name__ == "__main__":
    experiment_results = client.evaluate(
        target,
        data=os.environ.get("DATASET_NAME"),
        evaluators=[correctness_evaluator,],
        max_concurrency=4,
)
