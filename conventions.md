# Conventions

## Dataflow Events
Always remember to wire up any new events in dataflow.yml by:
1. Adding new events to the outputs list of the sending node
2. Adding new events to the inputs list of the receiving node and connecting them with sender_node/event_name format

This is especially important when adding new UI interactions that need to communicate between nodes.
