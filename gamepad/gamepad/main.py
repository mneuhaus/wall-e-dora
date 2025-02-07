from dora import Node
import pyarrow as pa
import time
from Gamepad import Gamepad

def main():
    node = Node()
    gp = Gamepad()

    while True:
        event = gp.getNextEvent()
        if event is None:
            time.sleep(0.01)
            continue
        print(f"Publishing gamepad event: {event}")
        node.send_output(
            output_id="gamepad_input", data=pa.array([str(event)]), metadata={}
        )

if __name__ == "__main__":
    main()
