from openai import OpenAI
import os
import json

OPENAI_KEY = os.environ['OPENAI_KEY']

openai = OpenAI(api_key=OPENAI_KEY)

fn = "/home/gabriel/projects/llmpc/trip_planner/data/trip_planning_reduced.json"
f = open(fn,'r')
data = json.load(f)

solutions = {}

SEED = 42
system_prompt = """
You are a diligent AI assistant. You will be given a task and your job is to complete the task as instructed, closely following any specified constraints.
Make sure to exactly adhere to the final answer output format provided by any examples in the task.

Specifically you will be asked to propose a trip plan given constraints on the number of days, flights and order of locations to visit.
Note that when flying from one city to another it counts as a day spent in both cities and will count towards the number of days required to visit both of those cities.
For example if we fly from city A to city B on day 7 the visit to city B will start on day 7 and the visit to city A will end on day 7.
Your only job is to focus on the constraints around cities to visit, number of days and ordering of the trip.
You do not need to investigate activities, accomodation etc, only focus on satisfying the stated trip constraints.
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
        max_tokens=1000,   # Adjust as needed
        seed=SEED
    )

    # The patch is in the assistant's reply
    resp = response.choices[0].message.content
    print(resp)
    solutions[k] = {}
    solutions[k]['num_cities'] = d['num_cities']
    solutions[k]['pred_5shot_pro'] = resp
    solutions[k]['cities'] = d['cities']
    solutions[k]['durations'] = d['durations']

with open("./output/solution.json",'w') as f:
    json.dump(solutions,f,indent=1)