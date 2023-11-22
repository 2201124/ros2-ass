#!/usr/bin/env python3
import rclpy
import numpy as np
import math
import time
import tf_transformations
from rclpy.node import Node
from rclpy.action import ActionClient
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from geometry_msgs.msg import PoseStamped,Quaternion
from nav2_msgs.action import NavigateToPose
from action_msgs.msg import GoalStatus
from tf_transformations import euler_from_quaternion, quaternion_from_euler






class MazeSolverNode(Node):
    def __init__(self):
        super().__init__('maze_solver_node')
        self.odom_subscription = self.create_subscription(Odometry, 'odom', self.odom_callback, 10)
        self.subscription = self.create_subscription(LaserScan, 'scan', self.laser_callback, 10)
        self.publisher_Twist = self.create_publisher(Twist, 'cmd_vel', 10)
        self.publisher_Pose = self.create_publisher(PoseStamped, 'move_base_simple/goal', 10)
        self._action_client = ActionClient(self, NavigateToPose, 'NavigateToPose')


        self.nav = BasicNavigator()
        self.current_pose = None
        self.avg_front = 0
        self.avg_back = 0
        self.avg_left = 0
        self.avg_right = 0

        self.front = 0
        self.left = 0
        self.right = 0



        self.current_x = 0
        self.current_y = 0
        self.current_z = 0
        self.current_orient_x = 0
        self.current_orient_y = 0
        self.current_orient_z = 0
        self.current_orient_w = 0
        self.left_turn = 0
        self.right_turn = 0
        self.left_turn_counter = 0



    def odom_callback(self, msg):
        self.current_x = msg.pose.pose.position.x
        self.current_y = msg.pose.pose.position.y
        self.current_z = msg.pose.pose.position.z
        self.current_orient_x = msg.pose.pose.orientation.x
        self.current_orient_y = msg.pose.pose.orientation.y
        self.current_orient_z = msg.pose.pose.orientation.z
        self.current_orient_w = msg.pose.pose.orientation.w


    def laser_callback(self, msg):
        ranges = msg.ranges
        num_ranges = len(ranges)
        section = num_ranges // 12
        sections = [ranges[i * section:(i + 1) * section] for i in range(12)]
        self.avg_right = np.mean(sections[9])
        self.avg_left = np.mean(sections[3])
        self.avg_front = np.mean(sections[0])
        self.avg_back = np.mean(sections[6])

        self.current_2oclock = np.mean(sections[11])
        self.current_10oclock = np.mean(sections[2])

        self.right = np.mean(sections[8] + sections[9] + sections[10])
        self.left = np.mean(sections[2] + sections[3] + sections[4])
        self.front = np.mean(sections[0] + sections[1] + sections[11])



    def rotate(self, angular_speed, time_needed=None):
        
        if time_needed is None:  # if time_needed is not provided, calculate it for a 90 degree turn
            angle = math.pi / 2  # 90 degrees in radians
            time_needed = (angle / abs(angular_speed*2))

        twist = Twist()
        twist.linear.x = 0.0
        twist.linear.y = 0.0
        twist.linear.z = 0.0
        twist.angular.x = 0.0
        twist.angular.y = 0.0
        twist.angular.z = angular_speed
        self.publisher_Twist.publish(twist)
        time.sleep(time_needed)
        # stop rotation
        twist.angular.z = 0.0
        self.publisher_Twist.publish(twist)
        print("Rotated 90 degrees")

    def rotate(self, angle):
        # rotation_matrix = tf_transformations.quaternion_matrix([self.current_orient_x, self.current_orient_y, self.current_orient_z, self.current_orient_w])
        # turn_angle = math.radians(angle)
        # turn_matrix = tf_transformations.rotation_matrix(turn_angle, [0, 0, 1])
        # new_rotation_matrix = np.dot(turn_matrix, rotation_matrix)
        # new_quaternion = tf_transformations.quaternion_from_matrix(new_rotation_matrix)
        # return new_quaternion
        angle_rad = math.radians(angle)

        # Create a quaternion for the rotation
        quaternion = tf_transformations.quaternion_from_euler(0, 0, angle_rad)

        return quaternion


    # def rotate_left_then_move_forward(self,angular_speed, duration):
    #     self.rotate(angular_speed, duration)
    #     print("Rotating rn")
    #     time.sleep(duration)
    #     self.update_command_velocity(0.2,0.0)
    #     time.sleep(3)
    #     print("I'm not breaking the loop hehe")
    #     print(self.avg_left)
    #     print(self.avg_front)
    def send_goal(self, x, y, theta):
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.pose.position.x = x
        goal_msg.pose.pose.position.y = y
        q = quaternion_from_euler(0, 0, theta)
        goal_msg.pose.pose.orientation = Quaternion(*q)

        self._action_client.wait_for_server()
        self._action_client.send_goal_async(goal_msg)
    
    



    def update_command_velocity(self, linear, angular):
        twist = Twist()
        twist.linear.x = linear
        twist.angular.z = angular
        self.publisher_Twist.publish(twist)



    def navigate(self):

        goal = PoseStamped()
        goal.header.frame_id = 'map'
        goal.header.stamp = self.nav.get_clock().now().to_msg()
        twist = Twist()
        print("Left Turn Status : ", self.left_turn)
        print("Right Turn Status : ", self.right_turn)
        if self.left < 1.4:
            if self.front > 0.6:   
                self.update_command_velocity(0.3,0.0)
                self.right_turn = 0
                print("LEFT DETECTED - MOVING FORWARD")
            elif self.front <0.6 and self.right_turn == 0:
                twist.linear.x = 0.0
                twist.linear.y = 0.0
                twist.linear.z = 0.0
                twist.angular.x = 0.0
                twist.angular.y = 0.0
                twist.angular.z = -0.8
                self.publisher_Twist.publish(twist)
                time.sleep(1)
                self.right_turn = 1
                print("FRONT & LEFT DETECTED - TURNING RIGHT")

        elif self.left > 1.2 and self.left_turn == 0:
                new_quaternion = self.rotate(-90)
                goal.pose.orientation.z = new_quaternion[2]
                goal.pose.orientation.w = new_quaternion[3]
                goal.pose.position.x = self.current_x
                goal.pose.position.y = self.current_y
                goal.pose.position.z = self.current_z
                self.nav.goToPose(goal)     
                print("Turning left")
                print(self.front)
                self.left_turn = 1

        if self.nav.isTaskComplete() and self.left_turn == 1:
            twist.linear.x = 0.3
            twist.linear.y = 0.0
            twist.linear.z = 0.0
            twist.angular.x = 0.0
            twist.angular.y = 0.0
            twist.angular.z = 0.0
            self.publisher_Twist.publish(twist)
            self.left_turn = 0
                # if self.left_turn == 1 and self.front > 1.2:
                #     self.update_command_velocity(0.3,0.0)  
                #     print("LEFT TURN COMPLETED - MOVING FORWARD")
                #     self.left_turn = 0

                    
                # elif self.left_turn == 0:
                #         print(self.left)
                #         twist.linear.x = 0.0
                #         twist.linear.y = 0.0
                #         twist.linear.z = 0.0
                #         twist.angular.x = 0.0
                #         twist.angular.y = 0.0
                #         twist.angular.z = 0.8
                #         self.publisher_Twist.publish(twist)
                #         time.sleep(0.5)
                #         self.left_turn = 1
                #         print("LEFT NOT DETECTED - TURNING LEFT")



    

        #Self.left turn is not updating to 0 






        

        #check if there's a wall to the left
            # - No : Turn left
            # - Yes : Check if wall infront
            #       - Yes : Turn right
            #       - No : Move forward

        # print("Left: ", self.avg_left)
        # print("Front: ", self.avg_front)

        # if self.avg_left < 0.9:
        #     if self.avg_front > 0.6:   
        #         self.update_command_velocity(0.2,0.0)
        #         print("LEFT DETECTED - MOVING FORWARD")
        #     else:
                
        #         self.rotate(-0.2)
                
        #         print("FRONT & LEFT DETECTED - TURNING RIGHT")

        # elif self.avg_left > 0.9 and self.left_turn == 0:
        #     self.rotate(0.2)
        #     print("LEFT NOT DETECTED - TURNING LEFT")

        # #Self.left turn is not updating to 0 


        # if self.avg_front > 0.6 and self.left_turn == 1:
        #     self.update_command_velocity(0.2,0.0)
        #     print("LEFT NOT DETECTED - MOVING FORWARD")
        #     self.left_turn = 0



        # if self.maze_completed == False:

        #     #Checks if there's a wall to the left
        #     if self.avg_left < 0.9 and self.current_10oclock < 0.6:
        #         #Checks if infront has anything
        #         if self.avg_front > 0.5 :
        #             self.update_command_velocity(0.2,0.0)
        #             print("LEFT DETECTED - MOVING FORWARD")


        #         elif self.avg_front < 0.5 :
        #             self.rotate(-0.2)
        #             #self.rotate(-0.2,2.0)
        #             print("LEFT & FRONT DETECTED - TURNING RIGHT")

        #         print(self.avg_left)

        #     elif self.avg_left > 0.6:
        #         self.rotate(0.4,2.0)
        #         print("Rotating first Pass")
        #         self.rotate(0.4,2.0)
        #         print("Rotating second Pass")
        #         self.left_turn = True
        #         print(self.left_turn)
        #         self.update_command_velocity(0.0,0.0)
        #         print("Stopped")


        #         if self.left_turn == True and self.avg_left > 0.6:
        #             self.update_command_velocity(0.2,0.0)
        #             print("Moving fast")
        #             time.sleep(3)
        #             self.update_command_velocity(0.0,0.0)
        #             print("Stopped")
        #             self.left_turn = False
                    

        #     if (self.avg_front <0.5):
        #         self.update_command_velocity(0.0,0.0)
        #         print("Stopped")

        #     if(self.avg_front > 3 and self.avg_left > 3 and self.avg_right > 3 and self.avg_back > 2):
        #         self.maze_completed = True
        #         print("Maze Completed")
        #         self.update_command_velocity(0.0,0.0)
    

                

def main(args=None):
    rclpy.init(args=args)
    maze_solver_node = MazeSolverNode()
    maze_solver_node.create_timer(1.0,maze_solver_node.navigate)
    rclpy.spin(maze_solver_node)
    
    
    maze_solver_node.destroy_node()
    rclpy.shutdown()

    

if __name__ == '__main__':
    main()