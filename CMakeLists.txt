cmake_minimum_required(VERSION 2.8.3)
project(casadi_mpc1)

## Find catkin and any catkin packages
find_package(catkin REQUIRED COMPONENTS
  rospy
  geometry_msgs
  nav_msgs
  std_msgs
)

## Declare a catkin package
catkin_package()

## Specify additional locations of header files
## Your package locations should be listed before other locations
include_directories(
  ${catkin_INCLUDE_DIRS}
)

## Mark Python scripts for installation
## in order to be installed
catkin_install_python(PROGRAMS
  src/casadi_mpc_node.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
