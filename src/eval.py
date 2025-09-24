import os
import re
from dotenv import load_dotenv
assert load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
from langsmith import Client
from openevals.llm import create_llm_as_judge
from openevals.prompts import CORRECTNESS_PROMPT
from langchain_openai import ChatOpenAI
import aiohttp
import asyncio

# Define the input and reference output pairs that you'll use to evaluate your app
client = Client()

llm = ChatOpenAI(
    model=os.environ.get("EVAL_MODEL_ID"),
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
            os.environ.get("APP_API_ENDPOINT"),
        ) as _:

            async def target(inputs: dict) -> dict:
                async with session.post(
                    os.path.join(os.environ.get("APP_API_ENDPOINT"),'api', 'ask'),
                    headers={"Content-Type": "application/json"},
                    json={"user_input": str(inputs)},
                ) as response:
                    html_answer = await response.text()
                    plaintext_answer = re.sub(r'<.*?>', '', html_answer)
                    return {"answer": plaintext_answer}

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

if __name__ == "__main__":
    asyncio.run(main())