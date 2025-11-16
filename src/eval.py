import os
import re
from dotenv import load_dotenv
assert load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
from langsmith import Client
from openevals.llm import create_llm_as_judge
from prompts import CORRECTNESS_PROMPT
import aiohttp
import asyncio
import json

# Define the input and reference output pairs that you'll use to evaluate your app
client = Client()

eval_model_id = os.environ.get("EVAL_MODEL_ID")
if not eval_model_id:
    raise ValueError("EVAL_MODEL_ID environment variable is not set")
elif eval_model_id.startswith("gpt-"):
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(
        model=eval_model_id,
        temperature=0.,
    )
else:
    from langchain_aws import ChatBedrockConverse
    llm = ChatBedrockConverse(
        model_id=eval_model_id,
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

async def main():
    eval_dataset_name = input("Enter eval dataset (options: \"test\", \"test-hard\",\"myegpt\"):")
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        async with await session.get(
            os.environ.get("SERVER_BASE_URL"),
        ) as _:

            results = []

            async def target(inputs: dict) -> dict:
                async with session.post(
                    os.path.join(os.environ.get("SERVER_BASE_URL"),'api', 'ask'),
                    headers={"Content-Type": "application/json"},
                    json={"user_input": str(inputs)},
                ) as response:
                    html_answer = await response.text()
                    plaintext_answer = re.sub(r'<.*?>', '', html_answer)
                    output = {"answer": plaintext_answer}
                    results.append({"input": inputs,
                                    "output": output})
                    return output

            await client.aevaluate(
                target,
                data=eval_dataset_name,
                evaluators=[scorer],
                max_concurrency=0,
                num_repetitions=1,
                experiment_prefix=eval_dataset_name,
                metadata={
                    'app_llm': os.environ.get("MODEL_ID"),
                    'eval_llm': os.environ.get("EVAL_MODEL_ID"),
                }
            )

            with open(f"../responses/{os.environ.get('LANGSMITH_PROJECT')}.json", "w") as f:
                json.dump(results, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())