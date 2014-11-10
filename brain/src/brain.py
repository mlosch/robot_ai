#!/usr/bin/env python
import roslib#; roslib.load_manifest('smach_tutorials')
import rospy
import smach
import smach_ros
import sys
from std_msgs.msg import Bool
from std_msgs.msg import Float64
from std_msgs.msg import String
from ir_converter.msg import Distance

######################## VARIABLES #########################

fl_side = 0
fr_side = 0
bl_side = 0
br_side = 0
l_front = 0
r_front = 0
recognize_object_pub = None
turn_pub = None
follow_wall_pub = None
go_forward_pub = None
turn_done = False
recognizing_done = False
object_detected = False
object_location = None
following_wall = False
stopping_done = False


######################## STATES #########################

# define state GoForward
class GoForward(smach.State):
    def __init__(self):
        smach.State.__init__(self, outcomes=['go_forward', 'stopping'])

    def execute(self, userdata):
        rospy.loginfo('Executing state GO_FORWARD')
        rospy.sleep(2.0)
        if ObstacleAhead():
            StopFollowWall()
            return 'stopping'
        else:
            FollowWall()
            return 'go_forward'

# define state Stopping
class Stopping(smach.State):
    def __init__(self):
        smach.State.__init__(self, outcomes=['stopping', 'obstacle_detected', 'object_detected'])

    def execute(self, userdata):
        global stopping_done
        rospy.loginfo('Executing state STOPPING')
        rospy.sleep(2.0)
        if stopping_done:
            stopping_done = False
            if object_detected:
                return 'object_detected'
            else:
                return 'obstacle_detected'
        else:
            return 'stopping'

# define state ObstacleDetected
class ObstacleDetected(smach.State):
    def __init__(self):
        smach.State.__init__(self, outcomes=['turning'])

    def execute(self, userdata):
        rospy.loginfo('Executing state ObstacleDetected')
        rospy.sleep(2.0)
        if CanTurnLeft():
            TurnLeft()
        if CanTurnRight():
            TurnRight()
        else:
            TurnBack()
        return 'turning'

# define state ObjectDetected
class ObjectDetected(smach.State):
    def __init__(self):
        smach.State.__init__(self, outcomes=['recognizing'])

    def execute(self, userdata):
        rospy.loginfo('Executing state ObjectDetected')
        rospy.sleep(2.0)
        RecognizeObject()
        return 'recognizing'

 # define state Turning
class Turning(smach.State):
    def __init__(self):
        smach.State.__init__(self, outcomes=['turning','go_forward'])

    def execute(self, userdata):
        global turn_done
        rospy.loginfo('Executing state Turning')
        rospy.sleep(2.0)
        if turn_done:
            turn_done = False
            return 'go_forward'       
        else:
            return 'turning'

 # define state Recognizing
class RecognizingObject(smach.State):
    def __init__(self):
        smach.State.__init__(self, outcomes=['recognizing','obstacle_detected'])

    def execute(self, userdata):
        global recognizing_done, object_detected
        rospy.loginfo('Executing state Recognizing')
        rospy.sleep(2.0)
        if recognizing_done:
            recognizing_done = False
            object_detected = False
            return 'obstacle_detected'       
        else:
            return 'recognizing'

######################## FUNCTIONS #########################

def CanTurnLeft():
    return True if fl_side > 0.20 and bl_side > 0.20 else False

def CanTurnRight():
    return True if fr_side > 0.20 and br_side > 0.20 else False

def ObstacleAhead():
    return True if l_front < 0.15 and r_front < 0.15 else False

def TurnLeft():
    turn_pub.publish(90.0)
    rospy.loginfo("Turning left")

def TurnRight():
    turn_pub.publish(-90.0)
    rospy.loginfo("Turning right")

def TurnBack():
    turn_pub.publish(180.0)
    rospy.loginfo("Turning back")

def FollowWall():
    global following_wall
    if not following_wall:
        following_wall = True
        go_forward_pub.publish(True)
        follow_wall_pub.publish(True)
        rospy.loginfo("Start Following Wall")

def StopFollowWall():
    global following_wall
    if following_wall:
        following_wall = False
        go_forward_pub.publish(False)
        follow_wall_pub.publish(False)
        rospy.loginfo("Stop Following Wall")

def RecognizeObject():
    recognize_object_pub.publish(object_location)
    rospy.loginfo("Start recognizing object")

def TurnDoneCallback(data):
    global turn_done
    turn_done = data
    rospy.loginfo("Turn done callback: %s", str(data))

def StoppingDoneCallback(data):
    global stopping_done
    stopping_done = data
    rospy.loginfo("Stopping done callback: %s", str(data))

def ObjectRecognizedCallback(data):
    global recognizing_done
    recognizing_done = data
    rospy.loginfo("Object Recognized: %s", str(data))

def ObjectDetectedCallback(data):
    global object_detected, object_location
    object_detected = True
    object_location = data
    rospy.loginfo("Object Detected: %s", str(data))

def IRCallback(data):
    global fl_side, fr_side, bl_side, br_side, l_front, r_front
    fl_side = data.fl_side;
    fr_side = data.fr_side;
    bl_side = data.bl_side;
    br_side = data.br_side;
    l_front = data.l_front;
    r_front = data.r_front;
    rospy.loginfo("IR callback: %d, %d, %d, %d, %d, %d", data.ch1, data.ch2, data.ch3 ,data.ch4 ,data.ch7,data.ch8)
    rospy.loginfo("vars: %d, %d", fl_side, fr_side)

def main():
    global turn_pub, follow_wall_pub, go_forward_pub, recognize_object_pub
    rospy.init_node('brain')
    
    sm = smach.StateMachine(outcomes=['error'])
    rospy.Subscriber("/robot_ai/distance", Distance, IRCallback)
    rospy.Subscriber("/controller/turn/done", Bool, TurnDoneCallback)
    rospy.Subscriber("/vision/recognizing_done", String, ObjectRecognizedCallback) # type?
    rospy.Subscriber("/vision/object_detected", String, ObjectDetectedCallback) # type?
    rospy.Subscriber("/controller/forward/stopped", Bool, StoppingDoneCallback)

    turn_pub = rospy.Publisher("/controller/turn/angle", Float64, queue_size=1)
    follow_wall_pub = rospy.Publisher("/controller/follow_wall/activate", Bool, queue_size=1)
    go_forward_pub = rospy.Publisher("/controller/forward/active", Bool, queue_size=1)
    recognize_object_pub = rospy.Publisher("/vision/recognize_object", String, queue_size=1) # type?

    with sm:
        smach.StateMachine.add('GO_FORWARD', GoForward(), 
                               transitions={'go_forward':'GO_FORWARD',
                               'stopping':'STOPPING'})
        smach.StateMachine.add('STOPPING', Stopping(), 
                               transitions={'stopping':'STOPPING',
                               'obstacle_detected':'OBSTACLE_DETECTED',
                               'object_detected':'OBJECT_DETECTED'})
        smach.StateMachine.add('OBSTACLE_DETECTED', ObstacleDetected(), 
                               transitions={'turning':'TURNING'})
        smach.StateMachine.add('TURNING', Turning(), 
                               transitions={'turning':'TURNING',
                               'go_forward':'GO_FORWARD'})
        smach.StateMachine.add('OBJECT_DETECTED', ObjectDetected(), 
                               transitions={'recognizing':'RECOGNIZING'})
        smach.StateMachine.add('RECOGNIZING', RecognizingObject(), 
                               transitions={'recognizing':'RECOGNIZING',
                               'obstacle_detected':'OBSTACLE_DETECTED'})

    # sleep to avoid that a decision is made before sensor data is received
    rospy.sleep(1.) 

    outcome = sm.execute()
    #rospy.spin() 

if __name__ == '__main__':
    main()