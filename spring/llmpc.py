import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from openai import OpenAI
import ast
import pandas as pd

OPENAI_KEY = os.environ['OPENAI_KEY']
openai = OpenAI(api_key=OPENAI_KEY)

#LLM parameters
SEED = 42
TEMPERATURE = 0.1

# System parameters
m = 1.0
k_spring = 5.0
dt = 0.1
x_goal = 2.0

# "MPC" parameters
H = 3  # horizon length
M = 2   # steps to apply before re-planning

# Cost parameters
Qx = 100.0
Qv = 100.0
Qu = 0.1

# Number of candidate sequences from LLM
K = 5

# Simulation parameters
T = 50

# Initial conditions
x0 = 1.0
v0 = 0.0

xs = [x0]
vs = [v0]
us = [0]
costs = [Qx*(x0 - x_goal)**2 + Qv*(v0)**2]

def simulate_sequence(x_init, v_init, u_sequence):
    # Simulate forward using the proposed controls and return the cost
    x = x_init
    v = v_init
    cost = 0.0
    for i, u in enumerate(u_sequence):
        # Compute cost at this step
        cost += Qu*(u**2)
        # Update state
        a = (u - k_spring*x)/m
        x = x + dt*v
        v = v + dt*a
    # Add terminal cost:
    cost += Qx*(x - x_goal)**2 + Qv*(v**2)
    return cost

def query_llm_for_plans(x_init, v_init, x_goal, H, K):
    # Prompt asking for K candidate sequences
    prompt = f"""
Given:
 - A mass-spring system with position x and velocity v.
 - Dynamics:
   x_(k+1) = x_k + dt * v_k
   v_(k+1) = v_k + (dt/m)*(u_k - k_spring*x_k)
 - Parameters: m={m}, k_spring={k_spring}, dt={dt}
 - Current state: x={x_init}, v={v_init}
 - Goal position: x_goal={x_goal}
 - Horizon: H={H}
 - The current spring force is {-k_spring*x_init}
 
 You control the force on the spring via the control sequence u = [u_0, u_1, ..., u_{H-1}].
 You must apply forces to get the spring to the goal position.
 Please propose {K} candidate control sequences, each being a list of length H.
 - Controls should be between 0 and 20
 - Return them as a Python dictionary with keys "sequence_1", "sequence_2", ..., "sequence_{K}", 
   where each value is a list of length H. Example:
   {{
     "sequence_1": [u_0, u_1, ..., u_{{H-1}}],
     "sequence_2": [u_0, u_1, ..., u_{{H-1}}],
     ...
   }}
Do not use ```python tags, no extra commentary, just return the dictionary.
"""

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        temperature=TEMPERATURE,
        max_tokens=500,
        seed=SEED
    )
    plan_str = response.choices[0].message.content.strip()
    print(prompt)
    print(plan_str)
    # Attempt parsing
    try:
        plans = ast.literal_eval(plan_str)
        # Expecting a dict with sequence_i keys
        if not isinstance(plans, dict):
            raise ValueError("LLM did not return a dictionary.")
        # Check each sequence is list of length H
        for i in range(1, K+1):
            seq_key = f"sequence_{i}"
            if seq_key not in plans:
                raise ValueError(f"Key {seq_key} not found.")
            seq = plans[seq_key]
            if not (isinstance(seq, list) and len(seq) == H):
                raise ValueError(f"{seq_key} is not a list of length {H}.")
    except Exception as e:
        print("Error parsing LLM output, returning zeros:", e)
        # If parsing fails, just return K zero sequences
        plans = {f"sequence_{i}": [0.0]*H for i in range(1,K+1)}
    return plans

def get_best_llm_plan(x, v):
    plans = query_llm_for_plans(x, v, x_goal, H, K)

    best_cost = float('inf')
    best_plan = [0.0]*H
    for i in range(1, K+1):
        candidate = plans[f"sequence_{i}"]
        cost = simulate_sequence(x, v, candidate)
        print(cost,candidate)
        if cost < best_cost:
            best_cost = cost
            best_plan = candidate

    return best_plan

# Simulation loop
x = x0
v = v0
for t in range(0, T, M):
    u_plan = get_best_llm_plan(x, v)

    steps_to_apply = min(M, T - t)
    for i in range(steps_to_apply):
        u = u_plan[i]
        a = (u - k_spring*x)/m
        x = x + dt*v
        v = v + dt*a

        c = Qx*(x - x_goal)**2 + Qv*(v)**2 + Qu*u**2

        xs.append(x)
        vs.append(v)
        us.append(u)
        costs.append(c)

# Animation
fig, ax = plt.subplots()
ax.set_xlim(-0.1, 2.5)
ax.set_ylim(-0.5, 0.5)
ax.set_aspect('equal', adjustable='box')
ax.set_title("LLM-controlled spring-mass system (with K candidate sequences)")

(line,) = ax.plot([], [], lw=2, color='blue')
(mass_plot,) = ax.plot([], [], 'ro', markersize=10)
goal_line = ax.axvline(x=x_goal, color='green', linestyle='--', label='Goal Position')
ax.legend()

def init():
    line.set_data([], [])
    mass_plot.set_data([], [])
    return line, mass_plot

def update(frame):
    pos = xs[frame]
    line.set_data([0, pos], [0, 0])
    mass_plot.set_data([pos], [0])
    return line, mass_plot

ani = FuncAnimation(fig, update, frames=len(xs), init_func=init, blit=True, interval=100)

plt.show()


# Store output
df = pd.DataFrame()
df['u'] = us
df['x'] = xs
df['v'] = vs
df['c'] = costs

df.to_csv("./output/llmpc.csv")