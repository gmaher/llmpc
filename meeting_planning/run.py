from openai import OpenAI
import os
import json

OPENAI_KEY = os.environ['OPENAI_KEY']

openai = OpenAI(api_key=OPENAI_KEY)

fn = "/home/gabriel/projects/llmpc/meeting_planning/data/meeting_planning_reduced.json"
f = open(fn,'r')
data = json.load(f)

solutions = {}

SEED = 42
system_prompt = """
You are a diligent AI assistant. You will be given a task and your job is to complete the task as instructed, closely following any specified constraints.
Make sure to exactly adhere to the final answer output format provided by any examples in the task.

"""
openai_model = "gpt-4o"

for k,d in list(data.items()):
    print(k)
    prompt = d['prompt_5shot']

    response = openai.chat.completions.create(
        model=openai_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,  # Adjust as needed
        max_tokens=2048,   # Adjust as needed
        seed=SEED
    )

    # The patch is in the assistant's reply
    resp = response.choices[0].message.content
    print(resp)
    solutions[k] = d
    solutions[k]['pred_5shot_pro'] = resp

with open("./output/solution.json",'w') as f:
    json.dump(solutions,f,indent=1)