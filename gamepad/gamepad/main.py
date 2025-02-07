from dora import Node
import pyarrow as pa
import time
from Gamepad import Gamepad

def main():
    node = Node()
    gp = Gamepad()

    for event in node:
        if event["type"] == "INPUT":
            if event["id"] == "TICK":
                print(
                    f"""Node received:
                id: {event["id"]},
                value: {event["value"]},
                metadata: {event["metadata"]}"""
                )
        event = gp.getNextEvent()

        print(f"Publishing gamepad event: {event}")
        node.send_output(
            output_id="gamepad_input", data=pa.array([str(event)]), metadata={}
        )

if __name__ == "__main__":
    main()
