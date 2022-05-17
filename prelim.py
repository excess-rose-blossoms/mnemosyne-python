from numpy import record
from ndn.app import NDNApp
from ndn.encoding.name import Name

# TODO: Implement the hash function
def hash(self, input):
    return input

# basic building block code for the resource records
class Logger(NDNApp):
    def __init__(self, logger_ID):
        NDNApp.__init__(face=None, keychain=None)
        self.logger_ID = logger_ID # TODO: Assign the logger ID properly
        self.record_list = []
        self.tails_list = []
        return

    # Given a log event, create and return an NDN record packet.
    def create_record(self, log_event, prior_node_1, prior_node_2):
        record_name = Name.from_str(self.logger_ID + "/" + "RECORD" + "/" + log_event) # TODO: Naming packet using correct convention
        payload = { "log_event": log_event, 
                    "prior_digest_1": hash(prior_node_1),
                    "prior_digest_2": hash(prior_node_2)
                }
        return self.prepare_data(record_name, content=payload, signer=None) # TODO: Signing packet

    # Given a log event, create an NDN record packet
    # Push the record to the DAG
    # Send the new information about the DAG out on SVS
    def insert_record(self, log_event):
        # tails_list = svs.update(tails_list)
        # record_list = svs.update(record_list)
        prior_node_1 = self.tails_list.pop() if (len(self.tails_list) > 0) else None
        prior_node_2 = self.tails_list.pop() if (len(self.tails_list) > 0) else None
        new_record = self.create_record(log_event,prior_node_1, prior_node_2)
        self.record_list.append(new_record)
        self.tails_list.append(new_record)
        # svs.publish(tails_list)
        # svs.publish(record_list)