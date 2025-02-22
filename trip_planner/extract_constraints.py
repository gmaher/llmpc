from openai import OpenAI
import os
import json
from lib import extract_constraints, parse_constraints

OPENAI_KEY = os.environ['OPENAI_KEY']

openai = OpenAI(api_key=OPENAI_KEY)

fn = "/home/gabriel/projects/llmpc/trip_planner/data/trip_planning_reduced.json"
f = open(fn,'r')
data = json.load(f)

output_data = {}
output_fn = "/home/gabriel/projects/llmpc/trip_planner/data/trip_planning_reduced.json"

for k,d in list(data.items()):
    print(k)
    task = d['prompt_0shot']

    constraints_dict = extract_constraints(task, openai)
    constraints_dict = parse_constraints(constraints_dict)

    print(task,constraints_dict)
    output_data[k] = d
    #output_data[k]['prompt_0shot'] = task
    #output_data[k]['prompt_5shot'] = d['prompt_5shot']
    output_data[k]['constraints'] = constraints_dict
    #output_data[k]['cities'] = d['cities']
    #output_data[k]['durations'] = d['durations']

with open(output_fn,'w') as f:
    json.dump(output_data, f, indent=1)