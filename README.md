# CasADi MPC ROS1 Package (NOT TESTED)

## Overview

This ROS1 package implements Model Predictive Control (MPC) using CasADi. The node computes optimal control inputs for a mobile robot based on the current state, goal state, and path. The control commands are then published to the robot for execution.

## Installation

### Dependencies

Ensure you have the following dependencies installed:

- ROS1 (Kinetic, Melodic, or Noetic)
- Python 2.7 or 3.x
- `casadi` (`pip install casadi`)
- `numpy` (`pip install numpy`)

### Building the Package

1. Clone the repository into your catkin workspace:

   ```bash
   cd ~/catkin_ws/src
   git clone <repository-url> casadi_mpc
   ```
2. Build the package:

   ```bash
   cd ~/catkin_ws
   catkin_make
   ```

## Usage

### Running the Node

To run the MPC node, execute the following command:

```bash
rosrun casadi_mpc mpc_node.py
```

### Subscribed Topics

- `/robot_pose` (geometry_msgs/PoseStamped): Current state of the robot.
- `/goal_pose` (geometry_msgs/PoseStamped): Goal state of the robot.
- `/path` (nav_msgs/Path): Path to be followed by the robot.

### Published Topics

- `/cmd_vel` (geometry_msgs/Twist): Control commands for the robot.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
```
