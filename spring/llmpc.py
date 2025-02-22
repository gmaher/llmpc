import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from openai import OpenAI
import ast
import pandas as pd
from lib import get_best_llm_plan

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

# Simulation loop
x = x0
v = v0
for t in range(0, T, M):
    u_plan = get_best_llm_plan(x, v, H, K, dt, m, k_spring, x_goal, Qx, Qv, Qu)

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

ani.save('./output/spring_mass_llmpc.gif', writer='ffmpeg', fps=10)

plt.show()


# Store output
df = pd.DataFrame()
df['u'] = us
df['x'] = xs
df['v'] = vs
df['c'] = costs

df.to_csv("./output/llmpc.csv")