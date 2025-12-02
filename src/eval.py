import os
import re
from dotenv import load_dotenv
assert load_dotenv(os.path.join(os.path.dirname(__file__), '.env_eval'))
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

async def clear_eval_memory(session, access_token: str):
    try:
        print('Attempting to clear user memory of eval user:',os.environ.get("EVAL_USERNAME"))
        await session.delete(
            os.path.join(os.environ.get("SERVER_BASE_URL"), "api", "erase_memory"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }
        )
    except Exception as e:
        print(f"Unable to erase memory of eval user: {e}")
    print("Successfully cleared eval user memory.")

def get_tmp_token()-> str:
    from datetime import timedelta
    from security import create_access_token
    access_token_expires = timedelta(minutes=15)
    access_token = create_access_token(
        data={"sub": os.environ.get("EVAL_USERNAME")}, expires_delta=access_token_expires
    )
    return access_token

async def main():
    access_token = get_tmp_token()
    eval_dataset_name = os.environ.get("EVAL_DATASET_NAME")
    if eval_dataset_name:
        print(f"Using eval dataset: {eval_dataset_name}")
    else:
        eval_dataset_name = input("Select eval dataset (options: \"test\", \"test-hard\", \"myegpt\", \"myegpt-16nov25\"):")
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        try:
            if os.environ.get("CLEAR_EVAL_MEMORY") == "true":
                await clear_eval_memory(session, access_token)
            else:
                print("Skipping eval user memory clearance.")
            async with await session.post(
                os.path.join(os.environ.get("SERVER_BASE_URL"),"eval"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}"
                },
            ) as _:
            
                results = []

                async def target(inputs: dict) -> dict:
                    async with session.post(
                        os.path.join(os.environ.get("SERVER_BASE_URL"),'api', 'ask'),
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {access_token}"
                        },
                        json={"user_input": str(inputs)},
                    ) as response:
                        raw_answer = await response.text()
                        processed_answer = re.sub(r'(?s).*?(?=💬)', '', raw_answer)
                        output = {"answer": processed_answer}
                        results.append({"input": inputs,
                                        "output": output})
                        return output

                await client.aevaluate(
                    target,
                    data=client.list_examples(dataset_name=eval_dataset_name, splits=[os.environ.get("EVAL_SPLIT")]),
                    evaluators=[scorer],
                    max_concurrency=0,
                    num_repetitions=1,
                    experiment_prefix=os.environ.get("LANGSMITH_PROJECT"),
                    metadata={
                        'app_llm': os.environ.get("MODEL_ID"),
                        'eval_llm': os.environ.get("EVAL_MODEL_ID"),
                    }
                )
            with open(f"../responses/{os.environ.get('LANGSMITH_PROJECT')}.json", "w") as f:
                json.dump(results, f, indent=2)

        except Exception as e:
            print(f"Error during evaluation: {e}")


if __name__ == "__main__":
    asyncio.run(main())