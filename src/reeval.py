from langsmith import Client

import os
from dotenv import load_dotenv
assert load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
from langsmith import Client
from openevals.llm import create_llm_as_judge
from openevals.prompts import CORRECTNESS_PROMPT
from langchain_openai import ChatOpenAI
import json

# 1. Create and/or select your dataset
ls_client = Client()

llm = ChatOpenAI(
    model=os.environ.get("EVAL_MODEL_ID"),
    temperature=0.,
)

# Load the failed examples JSON file
with open('src/responses.json', 'r') as f:
    failed_examples = json.load(f)

def target(inputs: dict) -> dict:
    print('dataset input: ',inputs)
    # Find matching input and return the output
    for example in failed_examples:
        if example.get('inputs').get('question') == inputs['question']:
            print(example)
            return {'answer': example.get('output', 'key does not exist')}
    
    # Return empty if no match found
    return {'answer':'I couldn\'t find the answer'}

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
    # Create langsmith dataset from failed examples and copy its ID here
    eval_dataset_name = "ds-husky-platinum-75"

    # 4. Run evaluation
    experiment = ls_client.evaluate(
        target,
        data=eval_dataset_name,
        evaluators=[scorer],
        experiment_prefix="re-evaluation",
        upload_results=True
    )

    # 5. Export results to a JSON file
    df = experiment.to_pandas()
    df[['inputs.question','reference.answer','reference.scoring','outputs.answer','feedback.score']].to_json('eval_results.json',orient='index',indent=2)