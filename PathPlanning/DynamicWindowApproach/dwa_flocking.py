# -*- coding: utf-8 -*- 

"""
Mobile robot motion planning sample with Dynamic Window Approach

author: Atsushi Sakai (@Atsushi_twi), Göktuğ Karakaşlı

"""

import math
from enum import Enum

import matplotlib.pyplot as plt
import numpy as np

show_animation = True


def dwa_control(x, config, goal, ob):
    """
    Dynamic Window Approach control
    """
    dw = calc_dynamic_window(x, config)

    u, trajectory = calc_control_and_trajectory(x, dw, config, goal, ob)

    return u, trajectory


class RobotType(Enum):
    circle = 0
    rectangle = 1


class Config:
    """
    simulation parameter class
    """

    def __init__(self):
        # robot parameter
        self.max_speed = 0.8  # [m/s]
        self.min_speed = -0.5  # [m/s]
        self.max_yaw_rate = 60.0 * math.pi / 180.0  # [rad/s]
        self.max_accel = 0.2  # [m/ss]
        self.max_delta_yaw_rate = 40.0 * math.pi / 180.0  # [rad/ss]
        self.v_resolution = 0.01  # [m/s]
        self.yaw_rate_resolution = 1.0 * math.pi / 180.0  # [rad/s]
        self.dt = 0.1  # [s] Time tick for motion prediction
        self.predict_time = 1.5  # [s]
        self.to_goal_cost_gain = 0.15
        self.speed_cost_gain = 1.0
        self.obstacle_cost_gain = 1.0
        self.robot_stuck_flag_cons = 0.0001  # constant to prevent robot stucked
        self.robot_type = RobotType.circle

        # if robot_type == RobotType.circle
        # Also used to check if goal is reached in both types
        self.robot_radius = 0.5  # [m] for collision check

        # if robot_type == RobotType.rectangle
        self.robot_width = 0.5  # [m] for collision check
        self.robot_length = 1.2  # [m] for collision check
        # obstacles [x(m) y(m), ....]
        objarry = []
        objarry.append([12, -3])
        objarry.append([13, -5])
        objarry.append([12.5, -8])
        objarry.append([14.5, -4])
        objarry.append([21, -5])
        objarry.append([22.5, -2])
        objarry.append([23, -8])
        objarry.append([24, -6])

        self.ob = np.array(objarry)

    @property
    def robot_type(self):
        return self._robot_type

    @robot_type.setter
    def robot_type(self, value):
        if not isinstance(value, RobotType):
            raise TypeError("robot_type must be an instance of RobotType")
        self._robot_type = value


config = Config()


def motion(x, n, u, dt):
    """
    motion model
    """
    x[n, 2] += u[1] * dt                          # Angle
    x[n, 0] += u[0] * math.cos(x[n, 2]) * dt      # X Position
    x[n, 1] += u[0] * math.sin(x[n, 2]) * dt      # Y Position
    x[n, 3] = u[0]                                # u[0], Velocity
    x[n, 4] = u[1]                                # u[1], Angular Velocity

    return x


def calc_dynamic_window(x, config):
    """
    calculation dynamic window based on current state x
    """

    # Dynamic window from robot specification
    Vs = [[config.min_speed, config.max_speed,
          -config.max_yaw_rate, config.max_yaw_rate]]
    Vs.append([config.min_speed, config.max_speed,
               -config.max_yaw_rate, config.max_yaw_rate])
    Vs.append([config.min_speed, config.max_speed,
               -config.max_yaw_rate, config.max_yaw_rate])
    Vs.append([config.min_speed, config.max_speed,
               -config.max_yaw_rate, config.max_yaw_rate])
    Vs.append([config.min_speed, config.max_speed,
               -config.max_yaw_rate, config.max_yaw_rate])
    Vs.append([config.min_speed, config.max_speed,
               -config.max_yaw_rate, config.max_yaw_rate])
    print("vs:", Vs)


    # Dynamic window from motion model
    Vd = [[x[0, 3] - config.max_accel * config.dt,
          x[0, 3] + config.max_accel * config.dt,
          x[0, 4] - config.max_delta_yaw_rate * config.dt,
          x[0, 4] + config.max_delta_yaw_rate * config.dt]]
    for i in range(1, 6):
        Vd.append([x[i, 3] - config.max_accel * config.dt,
             x[i, 3] + config.max_accel * config.dt,
             x[i, 4] - config.max_delta_yaw_rate * config.dt,
             x[i, 4] + config.max_delta_yaw_rate * config.dt])
    print("vd:", Vd)
    #  [v_min, v_max, yaw_rate_min, yaw_rate_max]
    dw = [[max(Vs[0][0], Vd[0][0]), min(Vs[0][1], Vd[0][1]),
          max(Vs[0][2], Vd[0][2]), min(Vs[0][3], Vd[0][3])],
          [max(Vs[1][0], Vd[1][0]), min(Vs[1][1], Vd[1][1]),
          max(Vs[1][2], Vd[1][2]), min(Vs[1][3], Vd[1][3])],
          [max(Vs[2][0], Vd[2][0]), min(Vs[2][1], Vd[2][1]),
          max(Vs[2][2], Vd[2][2]), min(Vs[2][3], Vd[2][3])],
          [max(Vs[3][0], Vd[3][0]), min(Vs[3][1], Vd[3][1]),
          max(Vs[3][2], Vd[3][2]), min(Vs[3][3], Vd[3][3])],
          [max(Vs[4][0], Vd[4][0]), min(Vs[4][1], Vd[4][1]),
          max(Vs[4][2], Vd[4][2]), min(Vs[4][3], Vd[4][3])],
          [max(Vs[5][0], Vd[5][0]), min(Vs[5][1], Vd[5][1]),
          max(Vs[5][2], Vd[5][2]), min(Vs[5][3], Vd[5][3])]]

    print("dw:", dw)

    return dw


def predict_trajectory(x_init, n, v, y, config):
    """
    predict trajectory with an input
    """

    x = np.array(x_init)
    trajectory = np.array(x)
    time = 0
    while time <= config.predict_time:
        x = motion(x, n, [v, y], config.dt)
        trajectory = np.vstack((trajectory, x))
        time += config.dt

    return trajectory


def calc_control_and_trajectory(x, dw, config, goal, ob):
    """
    calculation final input with dynamic window
    """

    x_init = x[:]
    min_cost = float("inf")
    best_u = []

    for i in range(6):
        inner = []
        for j in range(2):
            inner.append(0.0)
        best_u.append(inner)
    print("u: ", best_u)
    best_trajectory = np.array([x])
    # evaluate all trajectory with sampled input in dynamic window
    for n in range(6):
        for v in np.arange(dw[n][0], dw[n][1], config.v_resolution):
            for y in np.arange(dw[n][2], dw[n][3], config.yaw_rate_resolution):
                trajectory = predict_trajectory(x_init, n, v, y, config)
                # print("trajectory: ", trajectory)
                # calc cost
                to_goal_cost = config.to_goal_cost_gain * calc_to_goal_cost(trajectory, goal)
                speed_cost = config.speed_cost_gain * (config.max_speed - trajectory[-1, 3])
                ob_cost = config.obstacle_cost_gain * calc_obstacle_cost(trajectory, ob, config)

                final_cost = to_goal_cost + speed_cost + ob_cost

                # search minimum trajectory
                if min_cost >= final_cost:
                    min_cost = final_cost
                    best_u[n] = [v, y]
                    best_trajectory = trajectory
                    if abs(best_u[n][0]) < config.robot_stuck_flag_cons \
                            and abs(x[n, 3]) < config.robot_stuck_flag_cons:
                        # to ensure the robot do not get stuck in
                        # best v=0 m/s (in front of an obstacle) and
                        # best omega=0 rad/s (heading to the goal with
                        # angle difference of 0)
                        best_u[n][1] = -config.max_delta_yaw_rate
    return best_u, best_trajectory


def calc_obstacle_cost(trajectory, ob, config):
    """
    calc obstacle cost inf: collision
    """
    ox = ob[:, 0]
    oy = ob[:, 1]
    dx = trajectory[:, 0] - ox[:, None]
    dy = trajectory[:, 1] - oy[:, None]
    r = np.hypot(dx, dy)

    if np.array(r <= config.robot_radius).any():
        return float("Inf")

    min_r = np.min(r)
    return 1.0 / min_r  # OK


def calc_to_goal_cost(trajectory, goal):
    """
        calc to goal cost with angle difference
    """

    dx = goal[0] - trajectory[-1, 0]
    dy = goal[1] - trajectory[-1, 1]
    error_angle = math.atan2(dy, dx)
    cost_angle = error_angle - trajectory[-1, 2]
    cost = abs(math.atan2(math.sin(cost_angle), math.cos(cost_angle)))

    return cost


def plot_arrow(x, y, yaw, length=0.5, width=0.1):  # pragma: no cover

    for n in range(6):
        plt.arrow(x[n], y[n], length * math.cos(yaw[n]), length * math.sin(yaw[n]),
              head_length=width, head_width=width)
        plt.plot(x, y)


def plot_robot(x, y, yaw, config):  # pragma: no cover
    if config.robot_type == RobotType.rectangle:
        outline = np.array([[-config.robot_length / 2, config.robot_length / 2,
                             (config.robot_length / 2), -config.robot_length / 2,
                             -config.robot_length / 2],
                            [config.robot_width / 2, config.robot_width / 2,
                             - config.robot_width / 2, -config.robot_width / 2,
                             config.robot_width / 2]])
        Rot1 = np.array([[math.cos(yaw), math.sin(yaw)],
                         [-math.sin(yaw), math.cos(yaw)]])
        outline = (outline.T.dot(Rot1)).T
        outline[0, :] += x
        outline[1, :] += y
        plt.plot(np.array(outline[0, :]).flatten(),
                 np.array(outline[1, :]).flatten(), "-k")
    elif config.robot_type == RobotType.circle:
        circle = plt.Circle((x, y), config.robot_radius, color="b")
        plt.gcf().gca().add_artist(circle)
        out_x, out_y = (np.array([x, y]) +
                        np.array([np.cos(yaw), np.sin(yaw)]) * config.robot_radius)
        plt.plot([x, out_x], [y, out_y], "-k")


def main(robot_type=RobotType.circle):
    print(__file__ + " start!!")
    # initial state [x(m), y(m), yaw(rad), v(m/s), omega(rad/s)]
    x = np.empty((0, 5), int)
    x = np.append(x, np.array([[1.0, -1.0, 0.0, 0.0, 0.0]]), axis=0)
    x = np.append(x, np.array([[1.0, -3.0, 0.0, 0.0, 0.0]]), axis=0)
    x = np.append(x, np.array([[1.0, -5.0, 0.0, 0.0, 0.0]]), axis=0)
    x = np.append(x, np.array([[3.0, -1.0, 0.0, 0.0, 0.0]]), axis=0)
    x = np.append(x, np.array([[3.0, -3.0, 0.0, 0.0, 0.0]]), axis=0)
    x = np.append(x, np.array([[3.0, -5.0, 0.0, 0.0, 0.0]]), axis=0)
    # x = np.array([1.0, -1.0, 0.0, 0.0, 0.0])
    # goal position [x(m), y(m)]
    goal1 = np.array([26.5, -5])
    goal2 = np.array([20, -15])
    goal3 = np.array([2.5, -15])
    # input [forward speed, yaw_rate]

    config.robot_type = robot_type
    trajectory = np.array(x)
    ob = config.ob
    # goal 1
    while True:
        u, predicted_trajectory = dwa_control(x, config, goal1, ob)
        for n in range(6):
            x = motion(x, n, u[n], config.dt)  # simulate robot
        # x = motion(x, n, u[n], config.dt)  # simulate robot
        trajectory = np.vstack((trajectory, x))  # store state history

        if show_animation:
            plt.cla()
            # for stopping simulation with the esc key.
            plt.gcf().canvas.mpl_connect(
                'key_release_event',
                lambda event: [exit(0) if event.key == 'escape' else None])
            plt.plot(predicted_trajectory[:, 0], predicted_trajectory[:, 1], "-g")
            plt.plot(x[:, 0], x[:, 1], "xr")
            plt.plot(goal1[0], goal1[1], "xb")
            plt.plot(ob[:, 0], ob[:, 1], "ok")
            plot_robot(x[:, 0], x[:, 1], x[:, 2], config)
            plot_arrow(x[:, 0], x[:, 1], x[:, 2])
            plt.axis("equal")
            plt.grid(True)
            plt.pause(0.0001)

        # check reaching goal
        for n in range(6):
            dist_to_goal = math.hypot(x[n, 0] - goal1[0], x[n, 1] - goal1[1])
            if dist_to_goal <= config.robot_radius:
                print("Goal!!")
                break


    # goal 2
    while True:
        u, predicted_trajectory = dwa_control(x, config, goal2, ob)
        x = motion(x, u, config.dt)  # simulate robot
        trajectory = np.vstack((trajectory, x))  # store state history

        if show_animation:
            plt.cla()
            # for stopping simulation with the esc key.
            plt.gcf().canvas.mpl_connect(
                'key_release_event',
                lambda event: [exit(0) if event.key == 'escape' else None])
            plt.plot(predicted_trajectory[:, 0], predicted_trajectory[:, 1], "-g")
            plt.plot(x[0], x[1], "xr")
            plt.plot(goal2[0], goal2[1], "xb")
            plt.plot(ob[:, 0], ob[:, 1], "ok")
            plot_robot(x[0], x[1], x[2], config)
            plot_arrow(x[0], x[1], x[2])
            plt.axis("equal")
            plt.grid(True)
            plt.pause(0.0001)

        # check reaching goal
        dist_to_goal = math.hypot(x[0] - goal2[0], x[1] - goal2[1])
        if dist_to_goal <= config.robot_radius:
            print("Goal!!")
            break
    # goal 3 
    while True:
        u, predicted_trajectory = dwa_control(x, config, goal3, ob)
        x = motion(x, u, config.dt)  # simulate robot
        trajectory = np.vstack((trajectory, x))  # store state history

        if show_animation:
            plt.cla()
            # for stopping simulation with the esc key.
            plt.gcf().canvas.mpl_connect(
                'key_release_event',
                lambda event: [exit(0) if event.key == 'escape' else None])
            plt.plot(predicted_trajectory[:, 0], predicted_trajectory[:, 1], "-g")
            plt.plot(x[0], x[1], "xr")
            plt.plot(goal3[0], goal3[1], "xb")
            plt.plot(ob[:, 0], ob[:, 1], "ok")
            plot_robot(x[0], x[1], x[2], config)
            plot_arrow(x[0], x[1], x[2])
            plt.axis("equal")
            plt.grid(True)
            plt.pause(0.0001)

        # check reaching goal
        dist_to_goal = math.hypot(x[0] - goal3[0], x[1] - goal3[1])
        if dist_to_goal <= config.robot_radius:
            print("Goal!!")
            break



    print("Done")
    if show_animation:
        plt.plot(trajectory[:, 0], trajectory[:, 1], "-r")
        plt.pause(0.0001)

    plt.show()


if __name__ == '__main__':
    # main(robot_type=RobotType.rectangle)
     main(robot_type=RobotType.circle)
