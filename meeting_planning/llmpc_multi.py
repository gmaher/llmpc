import os
from openai import OpenAI
import json
from evaluate_meeting_planning_llmpc import process_constraints, parse_text_plan, validate_constraints

PLANS_PER_ITERATION = 5

system_prompt = f"""
You are an expert meeting planner assistant. Your goal is to create and refine plans to meet friends at different places in the city, taking into account travel times and meeting time constraints.
Your job is to iteratively create and modify a plan that meets with all the listed friends for the duration and location specified in the constraints. 

You will be given a limited number of iteration to make a full plan, these will be indicated by STEP X/TOTAL_STEPS.
For each step, propose {PLANS_PER_ITERATION} different possible plans. Make the plans meaningfully different from each other (e.g. meeting friends in different orders, starting with different meetings).

When no plan is given you should start by planning meetings with the first few required people.
When an existing plan is given you should consider:
1. Adding more meetings
2. Modifying meeting orders
3. Adjusting meeting durations
4. Trying completely different meeting sequences

If you believe you have the best possible plan make no modifications and output the existing plan {PLANS_PER_ITERATION} times.
Do not propose meeting with imaginary friends. 
Only propose meetings with friends mentioned in the task description.
Do not propose multiple meetings with the same friend.
If the plan already includes all mentioned friends, do not make any modifications or propose additional meetings.

PLAN FORMAT:
A plan includes a start, meeting, traveling and waiting steps.
* The start of a plan should be phrased as 'You start at <location> at <start_time>'
* A meeting step should be phrased as 'You meet <friend_name> for <time_spent> minutes from <start_time> to <end_time>.'
* A travel step should be phrased as 'You travel to <location> in <travel_time> minutes and arrive at <arrival_time>.'
* A waiting step should be phrased as 'You wait until <end_time>.'

Only use the above phrasing, e.g. do not mention 'You travel back to...' only mention 'You travel to...'

EXAMPLES:
Here are example input task descriptions and output plans:

You are visiting San Francisco for the day and want to meet as many friends as possible. Solve the problem by considering various different schedules and picking the best one to optimize your goals.

Travel distances (in minutes):
Marina District to Alamo Square: 15.
Marina District to Fisherman's Wharf: 10.
Marina District to Union Square: 16.
Marina District to Embarcadero: 14.
Marina District to Financial District: 17.
Marina District to Nob Hill: 12.
Alamo Square to Marina District: 15.
Alamo Square to Fisherman's Wharf: 19.
Alamo Square to Union Square: 14.
Alamo Square to Embarcadero: 17.
Alamo Square to Financial District: 17.
Alamo Square to Nob Hill: 11.
Fisherman's Wharf to Marina District: 9.
Fisherman's Wharf to Alamo Square: 20.
Fisherman's Wharf to Union Square: 13.
Fisherman's Wharf to Embarcadero: 8.
Fisherman's Wharf to Financial District: 11.
Fisherman's Wharf to Nob Hill: 11.
Union Square to Marina District: 18.
Union Square to Alamo Square: 15.
Union Square to Fisherman's Wharf: 15.
Union Square to Embarcadero: 11.
Union Square to Financial District: 9.
Union Square to Nob Hill: 9.
Embarcadero to Marina District: 12.
Embarcadero to Alamo Square: 19.
Embarcadero to Fisherman's Wharf: 6.
Embarcadero to Union Square: 10.
Embarcadero to Financial District: 5.
Embarcadero to Nob Hill: 10.
Financial District to Marina District: 15.
Financial District to Alamo Square: 17.
Financial District to Fisherman's Wharf: 10.
Financial District to Union Square: 9.
Financial District to Embarcadero: 4.
Financial District to Nob Hill: 8.
Nob Hill to Marina District: 11.
Nob Hill to Alamo Square: 11.
Nob Hill to Fisherman's Wharf: 11.
Nob Hill to Union Square: 7.
Nob Hill to Embarcadero: 9.
Nob Hill to Financial District: 9.

CONSTRAINTS: You arrive at Marina District at 9:00AM. Deborah will be at Alamo Square from 11:15AM to 1:30PM. You'd like to meet Deborah for a minimum of 45 minutes. Jason will be at Fisherman's Wharf from 11:00AM to 1:15PM. You'd like to meet Jason for a minimum of 75 minutes. Betty will be at Union Square from 2:00PM to 6:15PM. You'd like to meet Betty for a minimum of 90 minutes. Anthony will be at Embarcadero from 12:15PM to 9:30PM. You'd like to meet Anthony for a minimum of 105 minutes. Daniel will be at Financial District from 7:00AM to 10:15AM. You'd like to meet Daniel for a minimum of 120 minutes. Jessica will be at Nob Hill from 6:00PM to 10:00PM. You'd like to meet Jessica for a minimum of 105 minutes.

SOLUTION:You start at Marina District at 9:00AM. You travel to Fisherman's Wharf in 10 minutes and arrive at 9:10AM. You wait until 11:00AM. You meet Jason for 75 minutes from 11:00AM to 12:15PM. You travel to Alamo Square in 20 minutes and arrive at 12:35PM. You meet Deborah for 45 minutes from 12:35PM to 1:20PM. You travel to Union Square in 14 minutes and arrive at 1:34PM. You wait until 2:00PM. You meet Betty for 90 minutes from 2:00PM to 3:30PM. You travel to Embarcadero in 11 minutes and arrive at 3:41PM. You meet Anthony for 105 minutes from 3:41PM to 5:26PM. You travel to Nob Hill in 10 minutes and arrive at 5:36PM. You wait until 6:00PM. You meet Jessica for 105 minutes from 6:00PM to 7:45PM.

OUTPUT FORMAT:

For your response only output the keyword SOLUTION followed by {PLANS_PER_ITERATION} plans separated by '---', do not number the plans or add headers, only output the text of the {PLANS_PER_ITERATION} plans, make sure the plans are different from each other, do not output anything other than this format:

SOLUTION:
<insert first plan>
---
<insert second plan>
---
...
"""

instruction_prompt = """
STEP {step}/{total_steps}

You have been asked to solve the following meeting planning task, pay particular attention the constraints and propose 3 different possible plans according to the format described in the system prompt:
TASK:
{task}

Your current best meeting plan is:
{current_plan}

{feedback_string}

OUTPUT FORMAT:

For your response only output the keyword SOLUTION followed by {num_plans} plans separated by '---', do not number the plans or add headers, only output the text of the {num_plans} plans, make sure the plans are different from each other, do not output anything other than this format:

SOLUTION:
<insert first plan>
---
<insert second plan>
---
...
"""

# Parameters
NUM_PLANNING_STEPS = 9

SEED = 42

# Clean and recreate output directory
output_dir = "./output/llmpc"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Load trip planning data
with open("/home/gabriel/projects/llmpc/meeting_planning/data/meeting_planning_reduced.json", 'r') as f:
    data = json.load(f)

client = OpenAI(api_key=os.getenv("OPENAI_KEY"))
solutions = {}


# Run planner for each test example
#k = "meeting_planning_example_974"
#d = data[k]
for k, d in list(data.items()):
    print(f"\nProcessing example {k}")

    output_log = f"{output_dir}/plan_{k}.md"
    with open(output_log, 'w') as f:
        f.write(f"{d['prompt_0shot']}\n\n")

    current_plan = ""
    best_num_failed = float('inf')

    start_location, initial_time = d["constraints"][0]
    constraints = process_constraints(d["constraints"][1:])
    dist_matrix = d["dist_matrix"]

    feedback_string = ""
    # Run iterations of planning
    for iteration in range(NUM_PLANNING_STEPS):
        print(f"\nIteration {iteration + 1}")
        print(current_plan)
        print(feedback_string)
        prompt = instruction_prompt.format(
            step=iteration+1,
            total_steps=NUM_PLANNING_STEPS,
            task=d['prompt_0shot'],
            current_plan=current_plan if current_plan else "No plan created yet.",
            feedback_string=feedback_string,
            num_plans=PLANS_PER_ITERATION
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system_prompt},
                        {"role":"user","content":prompt}],
            temperature=0.5,
            max_tokens=3496,
            seed=SEED
        )

        content = response.choices[0].message.content

        with open(output_log, 'a') as f:
            f.write(f"\nIteration {iteration + 1}\n")
            f.write(f"{prompt}\n\n")
            f.write(f"{content}\n")

        if "SOLUTION:" in content:
            plans = content.split("SOLUTION:")[1].strip().split("---")
            plans = [p.strip() for p in plans]

            # Evaluate each plan
            best_plan = None
            best_num_failed = float('inf')
            for plan in plans:
                parsed_plan = parse_text_plan(plan)
                print(parsed_plan)
                failed_constraints = validate_constraints(parsed_plan, constraints, start_location, initial_time, dist_matrix)

                if len(failed_constraints) < best_num_failed:
                    best_num_failed = len(failed_constraints)
                    best_plan = plan
                    current_feedback = failed_constraints

            current_plan = best_plan
            
            if best_num_failed > 0:
                feedback_string = "Here is feedback on the best plan:\n* " + "\n* ".join(current_feedback)
            else:
                print("All constraints met, exiting")
                break
        else:
            current_plan = content.strip()

    solutions[k] = d
    solutions[k]['pred_5shot_pro'] = current_plan

# Save solutions
with open(f"./output/llmpc_solution_multi_{PLANS_PER_ITERATION}_{NUM_PLANNING_STEPS}.json", 'w') as f:
    json.dump(solutions, f, indent=1)

print("\nCompleted all examples!")