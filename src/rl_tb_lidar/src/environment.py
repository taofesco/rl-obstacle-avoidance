#! /usr/bin/env python
import yaml
import rospy
import time
import numpy as np
from nav_msgs.msg import Odometry
from std_srvs.srv import Empty as EmptySrv
from sensor_msgs.msg import LaserScan

from utils.teleporter import Teleporter
from utils.space import ActionSpace, StateSpace
from kobuki_msgs.msg import BumperEvent
from geometry_msgs.msg import Twist


C = -10
STEP_TIME = 0.0666

class TurtlebotLIDAREnvironment():
    def __init__(self, map, real_turtlebot, **kwargs):
        save_lidar = kwargs.setdefault('save_lidar', False)
        self.A = ActionSpace(**kwargs['ActionSpace'])
        self.S = StateSpace(save_lidar=save_lidar, real_turtlebot=real_turtlebot, **kwargs['StateSpace'])

        self.is_crashed = False
        if real_turtlebot:
            self.bumber_sub = rospy.Subscriber('mobile_base/events/bumper', BumperEvent, self.process_bump)
        else:
            self.teleporter = Teleporter(map)
            self.crash_tracker_sub = rospy.Subscriber('/odom', Odometry, self.crash_callback)
            self.reset_stage = rospy.ServiceProxy('reset_positions', EmptySrv)
        return

    def reward_function(self, velocities, crashed):
        if crashed:
            reward = C
        else:
            reward = velocities[0]*np.cos(velocities[1])*STEP_TIME
        return reward

    def process_bump(self, data):
        print ("Turtlebot is crashed!!!")
        if (data.state == BumperEvent.PRESSED):
            self.is_crashed = True
        else:
            self.is_crashed = False

    def crash_callback(self, data):
        if data.twist.twist.linear.z:
            self.is_crashed = True
        else:
            self.is_crashed = False

    def reset_env(self):
        try:
            self.teleporter.teleport_predefined()
        except (rospy.ServiceException) as e:
            print ("reset_simulation service call failed")
        state = self.S.state(self.A.prev_action)
        return state

    def step(self, action_idx):
        action = self.A.action(action_idx, execute=True)
        state = self.S.state(action)
        crashed = self.is_crashed
        reward = self.reward_function(action, crashed)
        return state, reward, crashed

    def handle_collision(self, last_action):
        action = self.A.action(last_action, execute=True)
        vel_cmd = Twist()
        # Apply the intensified reverse of action
        self.A.execute(action, intensify=-5)
        time.sleep(STEP_TIME)

        state = self.S.state(action)

        return state
