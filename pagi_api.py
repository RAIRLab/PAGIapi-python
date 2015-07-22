"""
Python PAGIworld API
"""

import math
import os
import socket
import time

# TODO: finish adding in valid sensors and forces
VALID_COMMANDS = ["sensorRequest", "addForce", "loadTask", "print", "findObj", "setState",
                  "getActiveStates", "setReflex", "removeReflex", "getActiveReflexes"]

VALID_SENSORS = ["S", "BP", "LP", "RP", "A", "MDN", "MPN"]
for i in range(5):
    VALID_SENSORS.append("L%d" % i)
    VALID_SENSORS.append("R%d" % i)
for i in range(0, 3020, 15):
    VALID_SENSORS.append("V%f" % (i / 100.))
# TODO: Ask John what are valid numbers for this
# for i in range(0, 15.10, 0.667):
#    VALID_SENSORS.append("P%f" % i)

VALID_FORCES = ["RHvec", "LHvec", "BMvec", "RHH", "LHH", "RHV", "LHV", "BMH", "BMV", "J", "BR",
                "RHG", "LHG"]

class PAGIWorld(object):
    """
    :type pagi_socket: socket.socket
    :type __message_fragment: str
    :type __task_file: str
    :type __command_stack: list
    :type message_stack: list
    """
    def __init__(self, ip_address="", port=42209):
        """

        :param ip:
        :param port:
        :return:
        """
        self.pagi_socket = None
        self.__message_fragment = ""
        self.__task_file = ""
        self.__command_stack = list()
        self.message_stack = list()
        self.connect(ip_address, port)
        self.agent = PAGIAgent(self)

    def connect(self, ip_address="", port=42209):
        """
        Create a socket to the given

        :param ip:
        :param port:
        :return:
        :raises: ConnectionRefusedError
        """
        if ip_address == "":
            ip_address = socket.gethostbyname(socket.gethostname())
        self.pagi_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.pagi_socket.connect((ip_address, port))
        self.pagi_socket.setblocking(True)

    def disconnect(self):
        """
        Close the socket to PAGIWorld and then reset internal variables (in case we just use
        connect directly without creating new PAGIWorld instance)

        :return:
        """
        self.pagi_socket.close()
        self.pagi_socket = None
        self.__message_fragment = ""
        self.__command_stack = list()
        self.message_stack = list()

    def __assert_open_socket(self):
        """
        Make sure we are operating on an existing socket connection
        :return:
        """
        if self.pagi_socket is None:
            raise RuntimeError("No open socket. Use connect() to open a new socket connection")

    def send_message(self, message):
        """
        Send a message to the socket

        :param message:
        :type message: str
        :return:
        """
        self.__assert_open_socket()
        command = message[:message.find(",")]
        if command == "" or command not in VALID_COMMANDS:
            raise RuntimeError("Invalid command found in the message '%s'" % message)

        end = message[len(command)+1:].find(",")
        if end == -1:
            secondary = message[len(command)+1:]
        else:
            secondary = message[len(command)+1:end]
        if command == "sensorRequest" and secondary not in VALID_SENSORS:
            raise RuntimeError("Invalid sensor '%s' in message '%s'" % (secondary, message))
        elif command == "addForce" and secondary not in VALID_FORCES:
            raise RuntimeError("Invalid force '%s' in message '%s'" % (secondary, message))

        # all messages must end with \n
        if message[-1] != "\n":
            message += "\n"
        self.__command_stack.append([command, secondary])
        self.pagi_socket.send(message.encode())

    def get_message(self, code="", block=True):
        """
        Returns the first available message from the socket. By default will block till we get a
        whole response from the socket

        :param code:
        :type code: str
        :param block:
        :type block: bool
        :return:
        :raises: BlockingIOError
        """
        while True:
            if block:
                while "\n" not in self.__message_fragment:
                    self.__message_fragment += self.pagi_socket.recv(4096).decode()
            else:
                self.__message_fragment += self.pagi_socket.recv(4096).decode()
            message_index = self.__message_fragment.find("\n")
            if message_index == -1:
                return ""
            else:
                response = self.__message_fragment[:message_index]
                self.__message_fragment = self.__message_fragment[message_index+1:]
                if code == "" or (response[:len(code)] == code and response[len(code)] == ","):
                    return response

    def load_task(self, task_file):
        """

        :param task_file:
        :type task_file: str
        :raises: FileNotFoundError
        """
        if not os.path.isfile(task_file):
            raise RuntimeError("Task file at '%s' was not found" % task_file)
        self.__task_file = task_file
        self.send_message("loadTask,%s" % task_file)

    def reset_task(self):
        """

        :raises: RuntimeError
        """
        if self.__task_file == "" or self.__task_file is None:
            raise RuntimeError("Cannot reset task, no previous task file found")
        self.load_task(self.__task_file)

    def print_text(self, text):
        """

        :param text:
        :type text: str
        :return:
        """
        text = str(text)
        self.send_message("print,%s" % text)
        self.get_message(code="print")

    def set_state(self, name, length):
        """

        :param name:
        :param length:
        :return:
        """
        raise NotImplementedError

    def remove_state(self, name):
        """

        :param name:
        :return:
        """
        self.send_message("setState,%s,0" % name)
        self.get_message(code="setState")

    def get_all_states(self):
        """

        :return:
        """
        self.send_message("getActiveStates")
        states = self.get_message(code="activeStates").split(",")
        return states[1:]

    def set_reflex(self, name, conditions, actions=""):
        """

        :param name:
        :param conditions:
        :param actions:
        :return:
        """
        raise NotImplementedError

    def remove_reflex(self, name):
        """

        :param name:
        :return:
        """
        self.send_message("removeReflex,%s" % name)
        self.get_message(code="removeReflex")

    def get_all_reflexes(self):
        """

        :return:
        """
        self.send_message("getActiveReflexes")
        reflexes = self.get_message(code="activeReflexes").split(",")
        return reflexes[1:]

    def create_item(self):
        """

        :return:
        """
        raise NotImplementedError

class PAGIAgent(object):
    """
    PAGIAgent

    :type pagi_world: PAGIWorld
    :type left_hand: PAGIAgentHand
    :type right_hand: PAGIAgentHand
    """
    def __init__(self, pagi_world):
        if not isinstance(pagi_world, PAGIWorld):
            raise ValueError("You must pass in a valid PagiWorld variable to PagiAgent")
        self.pagi_world = pagi_world
        self.left_hand = PAGIAgentHand('l', pagi_world)
        self.right_hand = PAGIAgentHand('r', pagi_world)

    def jump(self):
        """
        Causes the agent to try and jump. He will only be able to if his bottom edge is touching
        something solid, otherwise he'll do nothing.

        :return: bool True if agent has jumped (his bottom is touching something solid) otherwise
                        False
        """
        self.pagi_world.send_message("addForce,J,1000")
        response = self.pagi_world.get_message(code="J").split(",")
        return int(response[1]) == 1

    def reset_agent(self):
        """
        Resets agent state back to a starting position (looking upward with hands in starting
        position)
        :return:
        """
        self.reset_rotation()

    def reset_rotation(self):
        """
        Resets the agent's rotation back to 0 degrees (looking upward)
        :return:
        """
        self.rotate(0, absolute=True)

    def rotate(self, val, degrees=True, absolute=False):
        """
        Rotate the agent some number of degrees/radians. If absolute is True, then we rotate to
        position specified from 0 (looking up), otherwise rotate him relative to where he's looking.

        Therefore, if he's looking down at 180 degrees, and we tell him to rotate 90 degrees, if
        absolute is True, he'll be looking to the left at 90 degrees and if absolute is False,
        he'll be looking to the right at 270 degrees

              0
        90  agent  270
             180
        :param val:
        :type val: float
        :param degrees:
        :type degrees: bool
        :param absolute:
        :type absolute: bool
        :return:
        """
        if not degrees:
            val = val * 180. / math.pi
        if absolute:
            val %= 360.
            val -= self.get_rotation()
        self.pagi_world.send_message("addForce,BR,%f" % val)
        self.pagi_world.get_message(code="BR")

    def get_rotation(self, degrees=True):
        """
        Returns rotation in either degrees (0 - 359) or radians (0 - 2*pi) of agent (0 is looking
        upward)

        :param degrees:
        :type degrees: bool
        :return:
        """
        self.pagi_world.send_message("sensorRequest,A")
        response = self.pagi_world.get_message(code="BR").split(",")
        rotation = float(response)
        rotation %= 360
        if not degrees:
            rotation = rotation * math.pi / 180
        return rotation

    def move_paces(self, paces, direction='L'):
        """
        Attempts to move the agent some number of paces (defined as one width of his body) to
        either the left or right.

        :param paces:
        :type paces: int
        :param direction:
        :type direction: str
        :return:
        """
        assert_left_or_right(direction)
        val = 1 if direction[0].upper() == "R" else -1
        cnt = 0
        while cnt < paces:
            self.send_force(x=(val * 1000), absolute=True)
            time.sleep(2)
            cnt += 1

    def send_force(self, x=0, y=0, absolute=False):
        """
        Sends a vector force to the agent to move his body. If absolute is False, then vectors are
        relative to the direction agent is looking, thus +y is always in direction of top of agent,
        -y is bottom, +x is towards his right side, -x is his left side. If absolute is true, then
        vector +y is world up, -y is world bottom, +x is world right and -x is world left.

        :param x:
        :type x: float
        :param y:
        :type y: float
        :param absolute:
        :type absolute: bool
        :return:
        """
        if not absolute:
            self.pagi_world.send_message("addForce,BMvec%f,%f" % (x, y))
        else:
            rotation = self.get_rotation()
            if x != 0 and y != 0:
                ax = math.fabs(x)
                ay = math.fabs(y)
                hyp = math.sqrt(ax ** 2 + ay ** 2)
                angle = math.acos(ay / hyp)
                z = math.sin(angle) * ay
            else:
                if x > 0:
                    pass
                elif x < 0:
                    pass
                elif y < 0:
                    pass
                else:
                    pass

        self.pagi_world.get_message(code="BMvec")

    def get_position(self):
        """
        Gets x/y coordinates of the agent in the world
        :return: tuple(float, float) of coordinates of agent
        """
        self.pagi_world.send_message("sensorRequest,BP")
        response = self.pagi_world.get_message(code="BP").split(",")
        return float(response[1]), float(response[2])

    def get_periphal_vision(self):
        """
        Returns a list of 11 (rows) x 16 (columns) points which contains all of his periphal vision.
        vision[0][0] represents lower left of the vision field with vision[10][15] representing
        upper right
        :return: list of size 11 x 16
        """
        self.pagi_world.send_message("sensorRequest,MPN")
        response = self.pagi_world.get_message(code="MPN").split(",")
        return self.__process_vision(response, 16)

    def get_detailed_vision(self):
        """
        Returns a list of ?x? points which contains all of his detailed vision
        :return:
        """
        self.pagi_world.send_message("sensorRequest,MDN")
        response = self.pagi_world.get_message(code="MDN").split(",")
        return self.__process_vision(response, 21)

    @staticmethod
    def __process_vision(response, column_length):
        """

        :param response:
        :param column_length:
        :return:
        """
        vision = list()
        current = list()
        for j in range(1, len(response)):
            if (j - 1) % column_length == 0:
                if len(current) > 0:
                    vision.append(current)
                current = list()
            current.append(response[j])
        vision.append(current)
        return vision

    def center_hands(self):
        """
        Moves both of the agent's hands to the center of his body
        :return:
        """
        raise NotImplementedError

class PAGIAgentHand(object):
    """
    :type pagi_world: PAGIWorld
    """
    def __init__(self, hand, pagi_world):
        assert_left_or_right(hand)
        self.hand = hand[0].upper()
        self.pagi_world = pagi_world

    def get_position(self):
        """
        Gets the position of the hand relative to the agent
        :return: tupe(float, float) of the x, y coordinates of the hand
        """
        self.pagi_world.send_message("sensorRequest,%sP" % self.hand)
        response = self.pagi_world.get_message(code=("%sP" % self.hand)).split(",")
        return float(response[1]), float(response[2])

    def release(self):
        """
        Opens the hand, releasing anything it could be holding
        :return:
        """
        self.pagi_world.send_message("%sHR" % self.hand)
        self.pagi_world.get_message(code="%sHR" % self.hand)

    def grab(self):
        """
        Closes the hand, grabbing anything it is touching
        :return:
        """
        self.pagi_world.send_message("%sHG" % self.hand)
        self.pagi_world.get_message(code="%sHG" % self.hand)

    def send_force(self, x, y, absolute=False):
        """
        Sends a vector of force to the hand moving it
        :param x:
        :type x: float
        :param y:
        :type y: float
        :param absolute:
        :type absolute: bool
        :return:
        """
        if not absolute:
            self.pagi_world.send_message("%sHvec,%f,%f" % (self.hand, x, y))
        else:
            pass
        self.pagi_world.get_message(code="%sHvec" % self.hand)

def assert_left_or_right(direction):
    """
    Checks that the given direction is either left or right, and if it isn't, raise exception

    :param direction:
    :return:
    """
    if not direction.upper() == 'R' and not direction.upper() == 'L' \
            and not direction.upper() == 'RIGHT' and not direction.upper() == 'LEFT':
        raise ValueError("You can only use a L or R value for hands")
