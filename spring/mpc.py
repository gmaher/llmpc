import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import cvxpy as cp
import pandas as pd
from lib import solve_mpc

# ------------------------------------------------------------
# Model Predictive Control for a simple mass-spring system
#
# System:
#   We have a spring attached at one end, with a mass at the other.
#   We want to control the position of the mass by applying a force u.
#
# State:
#   x: Position of the mass (the length of the spring)
#   v: Velocity of the mass
#
# Dynamics:
#   x_{k+1} = x_k + dt * v_k
#   v_{k+1} = v_k + (dt/m) * (u_k - k*(x_k - x_ref))
#
# Parameters:
#   k_spring: stiffness of the spring
#   m: mass
#   dt: timestep
#
# MPC problem:
#   We have a horizon H. At each planning step, we solve:
#       min_{x,v,u} sum_{i=0}^{H-1} [(x_i - x_goal)^2 * Qx + (v_i)^2 * Qv + (u_i)^2 * Qu]
#   subject to system dynamics.
#
#   After solving for H steps, we apply the first M steps of the solution,
#   then re-solve.
#
# Goal:
#   Start at x=1, v=0, drive to x=2, and stay there.
#
# This code:
#   1. Sets up and solves the MPC problem repeatedly.
#   2. Simulates the system by applying the obtained controls.
#   3. Animates the result.
# ------------------------------------------------------------

# System parameters
m = 1.0       # mass
k_spring = 5.0  # spring stiffness
dt = 0.1      # time step
x_goal = 2.0  # target length

# MPC parameters
H = 3  # horizon length
M = 2   # number of steps to apply before replanning
Qx = 100.0  # state error weight for position
Qv = 100.0   # state error weight for velocity
Qu = 0.1   # control effort weight

# Simulation parameters
T = 50  # total simulation steps

# Initial conditions
x0 = 1.0
v0 = 0.0

# Storage for simulation results
xs = [x0]
vs = [v0]
us = [0]
costs = [Qx*(x0 - x_goal)**2 + Qv*(v0)**2]

# Setup MPC variables for convenience (we'll define them inside the loop too)
# State and control dimension
nx = 2 # (x, v)
nu = 1 # (u)

# Simulation loop
x = x0
v = v0
for t in range(0, T, M):
    # Solve MPC
    x_plan, v_plan, u_plan = solve_mpc(x, v, H, dt, m, k_spring, x_goal, Qx, Qv, Qu)
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

# ------------------------------------------------------------
# Animation
# ------------------------------------------------------------

fig, ax = plt.subplots()
ax.set_xlim(-0.1, 2.5)
ax.set_ylim(-0.5, 0.5)
ax.set_aspect('equal', adjustable='box')
ax.set_title("MPC-controlled spring-mass system")

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
    # Spring line
    line.set_data([0, pos], [0, 0])
    # Mass position
    mass_plot.set_data([pos], [0])
    return line, mass_plot

ani = FuncAnimation(fig, update, frames=len(xs), init_func=init, blit=True, interval=100)

ani.save('./output/spring_mass_mpc.gif', writer='ffmpeg', fps=10)

plt.show()


# Store output
df = pd.DataFrame()
df['u'] = us
df['x'] = xs
df['v'] = vs
df['c'] = costs

df.to_csv("./output/mpc.csv")
