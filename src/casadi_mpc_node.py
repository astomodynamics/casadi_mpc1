#!/usr/bin/env python

import rospy
from geometry_msgs.msg import PoseStamped, Twist
from nav_msgs.msg import Path
import numpy as np
import casadi as ca

class CasadiMPCNode:
    def __init__(self):
        rospy.init_node('casadi_mpc_node', anonymous=True)

        # MPC parameters
        self.horizon = 20
        self.dt = 0.1

        # State: [x, y, theta]
        # Input: [v, omega]

        # Weights for the cost function 
        self.Q = ca.diag([1, 1, 0.1])
        self.R = ca.diag([0.1, 0.1])
        self.Qf = ca.diag([1, 1, 0.1])

        # Box constraints
        self.x_min = 0
        self.x_max = 10
        self.y_min = 0
        self.y_max = 10
        self.theta_min = -ca.pi
        self.theta_max = ca.pi
        self.v_min = -1
        self.v_max = 1
        self.omega_min = -1
        self.omega_max = 1

        # current state and goal state
        self.current_state = ca.DM.zeros(3)
        self.goal_state = ca.DM.zeros(3)

        # Setup optimization problem
        self.setup_mpc()

        # ROS1 publishers and subscribers
        self.state_sub = rospy.Subscriber('/robot_pose', PoseStamped, self.current_state_callback)
        self.goal_sub = rospy.Subscriber('/goal_pose', PoseStamped, self.goal_state_callback)
        self.path_sub = rospy.Subscriber('/path', Path, self.path_callback)

        self.control_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)

        # Timer for continuous control in seconds
        self.control_timer = rospy.Timer(rospy.Duration(0.1), self.control_callback)

        rospy.loginfo('CasadiMPCNode has been initialized')

    def setup_mpc(self):
        # CasADi symbols
        self.x = ca.SX.sym('x', 3)
        self.u = ca.SX.sym('u', 2)

        # Differential drive kinematics
        x_dot = self.u[0] * ca.cos(self.x[2])
        y_dot = self.u[0] * ca.sin(self.x[2])
        theta_dot = self.u[1]

        x_next = self.x + self.dt * ca.vertcat(x_dot, y_dot, theta_dot)
        self.f = ca.Function('f', [self.x, self.u], [x_next])

        # Optimization variables
        self.opt_x = ca.SX.sym('opt_x', 3, self.horizon + 1)
        self.opt_u = ca.SX.sym('opt_u', 2, self.horizon)

        # Parameters
        self.p = ca.SX.sym('p', 3)  # Initial state
        self.ref = ca.SX.sym('ref', 3)  # Goal state

        # Cost function
        obj = 0
        for k in range(self.horizon):
            state_error = self.opt_x[:, k] - self.ref
            obj += ca.mtimes([state_error.T, self.Q, state_error]) + \
                   ca.mtimes([self.opt_u[:, k].T, self.R, self.opt_u[:, k]])

        state_error = self.opt_x[:, self.horizon] - self.ref
        obj += ca.mtimes([state_error.T, self.Qf, state_error])

        # Define the constraints
        g = []
        lbg = []
        ubg = []
        lbx = []
        ubx = []

        # Constraints
        g = []
        for k in range(self.horizon):
            g.append(self.opt_x[:, k + 1] - self.f(self.opt_x[:, k], self.opt_u[:, k]))

        # Initial condition constraint
        g.append(self.opt_x[:, 0] - self.p)

        # NLP problem
        nlp = {'x': ca.vertcat(ca.reshape(self.opt_x, -1, 1), ca.reshape(self.opt_u, -1, 1)),
               'f': obj,
               'g': ca.vertcat(*g),
               'p': ca.vertcat(self.p, self.ref)}

        # Create solver
        opts = {'ipopt.print_level': 0, 'print_time': 0}
        self.solver = ca.nlpsol('solver', 'ipopt', nlp, opts)

    def current_state_callback(self, msg):
        current_x = msg.pose.position.x
        current_y = msg.pose.position.y
        _, _, current_yaw = self.euler_from_quaternion(msg.pose.orientation)

        self.current_state = ca.DM([current_x, current_y, current_yaw])
        rospy.loginfo(f'Received state update: x={current_x:.2f}, y={current_y:.2f}, theta={current_yaw:.2f}')

    def goal_state_callback(self, msg):
        goal_x = msg.pose.position.x
        goal_y = msg.pose.position.y
        _, _, goal_yaw = self.euler_from_quaternion(msg.pose.orientation)

        self.goal_state = ca.DM([goal_x, goal_y, goal_yaw])
        rospy.loginfo(f'Received goal update: x={goal_x:.2f}, y={goal_y:.2f}, theta={goal_yaw:.2f}')

    def path_callback(self, msg):
        self.path = msg

        # Extract the path as reference ca.DM from the message
        self.ref_path = ca.DM([[pose.pose.position.x, pose.pose.position.y] for pose in msg.poses])

    def euler_from_quaternion(self, quaternion):
        x = quaternion.x
        y = quaternion.y
        z = quaternion.z
        w = quaternion.w

        sinr_cosp = 2 * (w * x + y * z)
        cosr_cosp = 1 - 2 * (x * x + y * y)
        roll = np.arctan2(sinr_cosp, cosr_cosp)

        sinp = 2 * (w * y - z * x)
        pitch = np.arcsin(sinp)

        siny_cosp = 2 * (w * z + x * y)
        cosy_cosp = 1 - 2 * (y * y + z * z)
        yaw = np.arctan2(siny_cosp, cosy_cosp)

        return roll, pitch, yaw

    def quaternion_from_euler(self, roll, pitch, yaw):
        cy = np.cos(yaw * 0.5)
        sy = np.sin(yaw * 0.5)
        cp = np.cos(pitch * 0.5)
        sp = np.sin(pitch * 0.5)
        cr = np.cos(roll * 0.5)
        sr = np.sin(roll * 0.5)

        q = [0] * 4
        q[0] = cy * cp * cr + sy * sp * sr
        q[1] = cy * cp * sr - sy * sp * cr
        q[2] = sy * cp * sr + cy * sp * cr
        q[3] = sy * cp * cr - cy * sp * sr

        return q

    def control_callback(self, event):
        # Solve MPC problem
        x0 = np.zeros((3, self.horizon + 1))
        x0[:, 0] = self.current_state
        u0 = np.zeros((2, self.horizon))

        res = self.solver(
            x0=ca.vertcat(ca.reshape(x0, -1, 1), ca.reshape(u0, -1, 1)),
            lbx=ca.vertcat([self.x_min, self.y_min, self.theta_min] * (self.horizon + 1),
                           [self.v_min, -self.omega_min] * self.horizon),
            ubx=ca.vertcat([self.x_max, self.y_max, self.theta_max] * (self.horizon + 1),
                           [self.v_min, self.omega_max] * self.horizon),
            lbg=0,
            ubg=0,
            p=ca.vertcat(self.current_state, self.goal_state)
        )

        # Extract optimal control input
        u_opt = np.array(res['x'][-2 * self.horizon:]).reshape(2, self.horizon)

        # Publish control input (linear and angular velocities)
        control_msg = Twist()
        control_msg.linear.x = float(u_opt[0, 0])  # Linear velocity
        control_msg.angular.z = float(u_opt[1, 0])  # Angular velocity
        self.control_pub.publish(control_msg)

        rospy.loginfo(f'Published velocities: linear={u_opt[0, 0]:.2f}, angular={u_opt[1, 0]:.2f}')

if __name__ == '__main__':
    try:
        node = CasadiMPCNode()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
