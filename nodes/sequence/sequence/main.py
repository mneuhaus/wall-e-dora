"""Sequence executor node with interruptible scene scheduling."""

from dora import Node

try:
    from sequence.runtime import SequenceScheduler, extract_sequence_id
except ModuleNotFoundError:
    from runtime import SequenceScheduler, extract_sequence_id


def main() -> None:
    node = Node()
    scheduler = SequenceScheduler()
    print('Sequence node started')

    for event in node:
        if event['type'] != 'INPUT':
            continue

        if event['id'] == 'trigger':
            seq_id = extract_sequence_id(event['value'])
            if not seq_id:
                print('Sequence: received empty trigger')
                continue

            if not scheduler.request_sequence(node, seq_id):
                print(f"Sequence: unknown sequence '{seq_id}'")
        elif event['id'] == 'tick':
            scheduler.emit_due_steps(node)


if __name__ == '__main__':
    main()
