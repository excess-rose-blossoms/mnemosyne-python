# Mnemosyne Python

Mnemosyne Python is a Python implementation of the Mnemosyne distributed logging framework for the Hydra distributed file framework. 
Logging for distributed sys- tems introduces a few new challenges compared to single-server settings which the design of Mnemosyne takes into account.
Distributing the logging among several loggers allows logging to continue even if some loggers fail. Mnemosyne loggers share updates with each other by publishing them using the NDN Sync protocol SVS, so that each can learn the whole logging history.
To ensure that events are immutable once they are logged, Mnemosyne uses a directed acyclic graph (DAG) of linked log events. Each event is cryptographically linked to at least two prior ones, similar to a blockchain, so that any modifications will easily be exposed.


## Implementation

The implementation consists of the following parts:

### Producer
A sample data producer for testing. Produces log events, each represented by an integer of increasing value.
It publishes these through SVS with the prefix "/svs/mnemosyne/log_events"


### Record Store
Provides storage functionality to the consumer class to store and retrieve records. Each consumer has its own RecordStore object. Implemented using a simple dict, but in the final version this will use some sort of persistent storage. Gives the following functionality:

store_record(new_record):
stores the record in persistent storage, in both the record and tails section. called when a new record is created -- either by the logger the store belongs to or receiving an ADD-REC update from another logger.

pop_tail_record(tail_record_name):
deletes the tail record of name "tail_record_name" from the tail section of persistent storage. returns said tail record. called upon receiving a DEL-TAIL update from another logger, or upon adding a new node that uses the node with name "tail_record_name" as its prior node link.

### Consumer
update_records(record_changes):
takes in a list of record changes and makes appropriate changes to the storage. the changes are in a list format. called upon receiving an SVS record group update from another logger.


### Record
Represents a log record. It contains a Name, two pointers to previous records (Names), and an event.
A Record objects also has a RecordTlv object, which is the actual data packet that will be encoded
and stored/shared. This class also has several functions for working with Records.
