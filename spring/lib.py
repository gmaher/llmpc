import numpy as np
import cvxpy as cp
import os
from openai import OpenAI
import ast

SEED = 42
TEMPERATURE = 0.1

def simulate_sequence(x_init, v_init, u_sequence, dt, m, k_spring, x_goal, Qx, Qv, Qu):
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

def solve_mpc(x_init, v_init, H, dt, m, k_spring, x_goal, Qx, Qv, Qu):
    # Variables
    x_var = cp.Variable((H+1,)) # positions
    v_var = cp.Variable((H+1,)) # velocities
    u_var = cp.Variable((H,))   # control inputs

    # Objective
    cost = 0
    constraints = []
    # Initial conditions
    constraints += [x_var[0] == x_init]
    constraints += [v_var[0] == v_init]

    # Dynamics and costs
    for i in range(H):
        # Cost
        cost += Qu * (u_var[i])**2

        # Dynamics
        # x_{k+1} = x_k + dt*v_k
        constraints += [x_var[i+1] == x_var[i] + dt*v_var[i]]
        # v_{k+1} = v_k + (dt/m)*(u_k - k_spring*(x_k - x_0))
        constraints += [v_var[i+1] == v_var[i] + (dt/m)*(u_var[i] - k_spring*(x_var[i]))]

    # Terminal cost (for stability)
    cost += Qx*(x_var[H] - x_goal)**2 + Qv*(v_var[H])**2

    # Solve MPC
    prob = cp.Problem(cp.Minimize(cost), constraints)
    prob.solve(solver=cp.OSQP, warm_start=True)

    # Extract solution
    if prob.status not in ["infeasible", "unbounded"]:
        u_plan = u_var.value
        x_plan = x_var.value
        v_plan = v_var.value
    else:
        # If infeasible, return zeros or something stable
        u_plan = np.zeros(H)
        x_plan = np.zeros(H+1)
        v_plan = np.zeros(H+1)

    return x_plan, v_plan, u_plan

def query_llm_for_plans(x_init, v_init, H, K, dt, m, k_spring, x_goal):
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

    OPENAI_KEY = os.environ['OPENAI_KEY']
    openai = OpenAI(api_key=OPENAI_KEY)

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

def get_best_llm_plan(x, v, H, K, dt, m, k_spring, x_goal, Qx, Qv, Qu):
    plans = query_llm_for_plans(x, v, H, K, dt, m, k_spring, x_goal)

    best_cost = float('inf')
    best_plan = [0.0]*H
    for i in range(1, K+1):
        candidate = plans[f"sequence_{i}"]
        cost = simulate_sequence(x, v, candidate, dt, m, k_spring, x_goal, Qx, Qv, Qu)
        print(cost,candidate)
        if cost < best_cost:
            best_cost = cost
            best_plan = candidate

    return best_plan