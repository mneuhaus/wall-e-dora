"""Main module for the Gamepad Node.

Reads raw gamepad events using the Gamepad library and publishes them
as string representations via the 'gamepad_input' Dora output.
"""

from dora import Node
import pyarrow as pa
import time
from Gamepad import Gamepad  # Assuming Gamepad.py is in the same directory


def main():
    """Main function for the Gamepad Node.

    Initializes the Gamepad library and the Dora node, then enters a loop
    reading the next gamepad event and sending it as a string output.
    """
    node = Node()
    gp = Gamepad()  # Assumes joystick 0 by default

    for event in node:
        event = gp.getNextEvent()
        node.send_output(
            output_id="gamepad_input", data=pa.array([str(event)]), metadata={}
        )

if __name__ == "__main__":
    main()
