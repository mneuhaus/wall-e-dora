"""Sequence executor node with interruptible scene scheduling."""

from dora import Node

try:
    from sequence.runtime import SequenceScheduler, extract_first_payload, extract_sequence_id
    from sequence.soundtrack_analysis import warm_soundtrack_analysis_cache
except ModuleNotFoundError:
    from runtime import SequenceScheduler, extract_first_payload, extract_sequence_id
    from soundtrack_analysis import warm_soundtrack_analysis_cache


def main() -> None:
    try:
        analyzed_tracks = warm_soundtrack_analysis_cache()
        print(f'Sequence: warmed soundtrack analysis cache for {analyzed_tracks} track(s)')
    except Exception as error:
        print(f'Sequence: soundtrack analysis warmup skipped: {error}')

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
        elif event['id'] == 'dance_mode':
            payload = extract_first_payload(event['value'])
            if isinstance(payload, dict) and payload.get('active'):
                if not scheduler.request_dance(node, payload):
                    print(f"Sequence: invalid dance payload '{payload}'")
            else:
                scheduler.cancel_active(node, reason='dance-stop')
        elif event['id'] == 'emergency_stop':
            scheduler.cancel_active(node, reason='emergency-stop')
        elif event['id'] == 'tick':
            scheduler.emit_due_steps(node)


if __name__ == '__main__':
    main()
