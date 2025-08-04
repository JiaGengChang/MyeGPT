import os
import re
import requests
from dotenv import load_dotenv
assert load_dotenv('.env')
from langsmith import Client
from openevals.llm import create_llm_as_judge
from openevals.prompts import CORRECTNESS_PROMPT
from langchain_aws import ChatBedrockConverse

# Define the input and reference output pairs that you'll use to evaluate your app
client = Client()

# Application logic
def target(inputs: dict) -> dict:
    response = requests.post(
        os.environ.get("APPLICATION_API_URL"),
        headers={"Content-Type": "application/json"},
        json={"user_input": inputs["question"]},
    )
    answer = response.json().get("response", "No response from API")
    # Remove HTML tags
    clean_answer = re.sub(r'<.*?>', '', answer)
    return {"answer": clean_answer}

llm = ChatBedrockConverse(
    model_id=os.environ.get("MODEL_ID"),
    temperature=0.,
)

# a correctness score from 0 to 1, where 1 is the best
def scorer(inputs: dict, outputs: dict, reference_outputs: dict):
    evaluator = create_llm_as_judge(
        prompt=CORRECTNESS_PROMPT,
        judge=llm,
        feedback_key="score",
        continuous=True,
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
        evaluators=[scorer],
        max_concurrency=1,
        experiment_prefix=os.environ.get("APPLICATION_API_URL").replace("https://", "").replace("/", "_"),
        metadata={
            'model': os.environ.get("MODEL"),
        }
)
