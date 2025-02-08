from dora import Node
import pyarrow as pa
import time
from Gamepad import Gamepad

def main():
    node = Node()
    gp = Gamepad()

    for event in node:
        event = gp.getNextEvent()
        node.send_output(
            output_id="gamepad_input", data=pa.array([str(event)]), metadata={}
        )

if __name__ == "__main__":
    main()
