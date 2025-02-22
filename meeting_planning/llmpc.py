import os
from openai import OpenAI
import json
from evaluate_meeting_planning_llmpc import process_constraints, parse_text_plan, validate_constraints

system_prompt = """
You are an expert meeting planner assistant. Your goal is to create and refine plans to meet friends at different places in the city, taking into account travel times and meeting time constraints.
Your job is to iteratively create and modify a plan that maximizes the number of friends that can be met given the constraints. 

You will be given a limited number of iteration to make a full plan, these will be indicated by STEP X/TOTAL_STEPS.
You can progressively build up the plan, but make sure that on the final step you propose a full plan that meets with as many people as possible given the constraints.

When no plan is given you should start by planning meetings with the first few required people.
When an existing plan is given you should consider adding more meetings or modifying the plan so that more meetings can be added.
If you believe you have the best possible plan make no modifications and simply output the existing plan.
Do not propose meeting with imaginary friends. 
Only propose meetings with friends mentioned in the task description.
Do not propose multiple meetings with the same friend, e.g. DO NOT say 'You meet <friend_name> again for ... .
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
Alamo Square to Marina District: 15.
Alamo Square to Fisherman's Wharf: 19.
Alamo Square to Union Square: 14.
Fisherman's Wharf to Marina District: 9.
Fisherman's Wharf to Alamo Square: 20.
Fisherman's Wharf to Union Square: 13.
Union Square to Marina District: 18.
Union Square to Alamo Square: 15.
Union Square to Fisherman's Wharf: 15.

CONSTRAINTS: You arrive at Marina District at 9:00AM. Jessica will be at Alamo Square from 2:30PM to 8:15PM. You'd like to meet Jessica for a minimum of 75 minutes. Ronald will be at Fisherman's Wharf from 3:15PM to 6:30PM. You'd like to meet Ronald for a minimum of 60 minutes. Mary will be at Union Square from 7:00PM to 10:00PM. You'd like to meet Mary for a minimum of 45 minutes.

SOLUTION:You start at Marina District at 9:00AM. You travel to Alamo Square in 15 minutes and arrive at 9:15AM. You wait until 2:30PM. You meet Jessica for 75 minutes from 2:30PM to 3:45PM. You travel to Fisherman's Wharf in 19 minutes and arrive at 4:04PM. You meet Ronald for 60 minutes from 4:04PM to 5:04PM. You travel to Union Square in 13 minutes and arrive at 5:17PM. You wait until 7:00PM. You meet Mary for 45 minutes from 7:00PM to 7:45PM.

You are visiting San Francisco for the day and want to meet as many friends as possible. Solve the problem by considering various different schedules and picking the best one to optimize your goals.

Travel distances (in minutes):
Marina District to Alamo Square: 15.
Marina District to Fisherman's Wharf: 10.
Marina District to Union Square: 16.
Marina District to Embarcadero: 14.
Alamo Square to Marina District: 15.
Alamo Square to Fisherman's Wharf: 19.
Alamo Square to Union Square: 14.
Alamo Square to Embarcadero: 17.
Fisherman's Wharf to Marina District: 9.
Fisherman's Wharf to Alamo Square: 20.
Fisherman's Wharf to Union Square: 13.
Fisherman's Wharf to Embarcadero: 8.
Union Square to Marina District: 18.
Union Square to Alamo Square: 15.
Union Square to Fisherman's Wharf: 15.
Union Square to Embarcadero: 11.
Embarcadero to Marina District: 12.
Embarcadero to Alamo Square: 19.
Embarcadero to Fisherman's Wharf: 6.
Embarcadero to Union Square: 10.

CONSTRAINTS: You arrive at Marina District at 9:00AM. Ronald will be at Alamo Square from 4:15PM to 9:45PM. You'd like to meet Ronald for a minimum of 90 minutes. Mary will be at Fisherman's Wharf from 11:15AM to 1:30PM. You'd like to meet Mary for a minimum of 45 minutes. Deborah will be at Union Square from 11:00AM to 1:15PM. You'd like to meet Deborah for a minimum of 75 minutes. Jason will be at Embarcadero from 2:00PM to 6:15PM. You'd like to meet Jason for a minimum of 90 minutes.

SOLUTION:You start at Marina District at 9:00AM. You travel to Union Square in 16 minutes and arrive at 9:16AM. You wait until 11:00AM. You meet Deborah for 75 minutes from 11:00AM to 12:15PM. You travel to Fisherman's Wharf in 15 minutes and arrive at 12:30PM. You meet Mary for 45 minutes from 12:30PM to 1:15PM. You travel to Embarcadero in 8 minutes and arrive at 1:23PM. You wait until 2:00PM. You meet Jason for 90 minutes from 2:00PM to 3:30PM. You travel to Alamo Square in 19 minutes and arrive at 3:49PM. You wait until 4:15PM. You meet Ronald for 90 minutes from 4:15PM to 5:45PM.

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

For your response only output the keyword SOLUTION and the plan, do not output anything else:

SOLUTION:
<your complete meeting plan here>

"""

instruction_prompt = """
STEP {step}/{total_steps}

You have been asked to solve the following meeting planning task, pay particular attention the constraints and propose the new few steps of the plan:
TASK:
{task}

Your current meeting plan is:
{current_plan}

{feedback_string}
"""

# Parameters
NUM_PLANNING_STEPS = 15  
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
for k, d in list(data.items()):
#k = "meeting_planning_example_394"
#d = data[k]
    print(f"\nProcessing example {k}")

    output_log = f"{output_dir}/plan_{k}.md"
    with open(output_log, 'w') as f:
        f.write(f"{d['prompt_0shot']}\n\n")

    current_plan = ""

    start_location, initial_time = d["constraints"][0]
    constraints = process_constraints(d["constraints"][1:])
    dist_matrix = d["dist_matrix"]

    feedback_string = ""
    # Run iterations of planning
    for iteration in range(NUM_PLANNING_STEPS):
        print(f"\nIteration {iteration + 1}")
        
        prompt = instruction_prompt.format(
            step=iteration+1,
            total_steps=NUM_PLANNING_STEPS,
            task=d['prompt_0shot'],
            current_plan=current_plan if current_plan else "No plan created yet.",
            feedback_string=feedback_string
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system_prompt},
                        {"role":"user","content":prompt}],
            temperature=0.4,
            max_tokens=4096,
            seed=SEED
        )

        content = response.choices[0].message.content

        with open(output_log, 'a') as f:
            f.write(f"\nIteration {iteration + 1}\n")
            f.write(f"{prompt}\n\n")
            f.write(f"{content}\n")

        if "SOLUTION:" in content:
            current_plan = content.split("SOLUTION:")[1].strip()
            parsed_plan = parse_text_plan(content)
            failed_constraints = validate_constraints(parsed_plan, constraints, start_location, initial_time, dist_matrix)
            print(current_plan)
            print(parsed_plan)
            print(failed_constraints)
            if len(failed_constraints)>0:
                feedback_string = "Here is feedback on the plan:\n" + "\n* ".join(failed_constraints)

            if len(failed_constraints)==0:
                print("all constraints met exiting")
                break
        else:
            current_plan = content.strip()

    solutions[k] = d
    solutions[k]['pred_5shot_pro'] = content

# Save solutions
with open(f"./output/llmpc_solution_{NUM_PLANNING_STEPS}.json", 'w') as f:
    json.dump(solutions, f, indent=1)

print("\nCompleted all examples!")