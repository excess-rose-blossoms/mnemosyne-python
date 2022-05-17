from numpy import record
from ndn.app import NDNApp
from ndn.encoding.name import Name

# basic building block code for the resource records
class Logger(NDNApp):
    def __init__(self, logger_ID):
        NDNApp.__init__(face=None, keychain=None)
        self.logger_ID = logger_ID # TODO
        self.record_list = []
        self.tails_list = []
        return
    
    # TODO
    def hash(self, input):
        return input

    def receive_event(self, log_event):
        # self.tails_list = svs.receive(tails_list)
        prior_node_1 = self.tails_list.pop()
        prior_node_2 = self.tails_list.pop()
        new_record = self.create_record(log_event, prior_node_1, prior_node_2)
        self.record_list.append(new_record)
        self.tails_list.append(new_record)
        # svs.publish(tails_list)

    def create_record(self, log_event, prior_node_1, prior_node_2):
        record_name = Name.from_str(self.logger_ID + "/" + "RECORD" + "/" + log_event) # TODO
        prior_digest_1 = hash(prior_node_1)
        prior_digest_2 = hash(prior_node_2)
        payload = { "log_event": log_event, 
                    "prior_digest_1": prior_digest_1, 
                    "prior_digest_2": prior_digest_2
                }
        self.prepare_data(record_name, content=payload, signer=None) #TODO: signing
        return {"rec_name": record_name, "rec_payload": payload}
    def create_record(self, log_event):
        # SVS event
        record_name = Name.from_str(self.logger_ID + "/" + "RECORD" + log_event) # TODO: replace log_event.id with an actual identifier from the log event received
        # TODO: assign prior record digests based on the tails + turn them into digests
        # TODO: conditional logic depending on whether two tails are even available
        payload = {"log_event": log_event, "prior_digest_1": None, "prior_digest_2": None}
        # TODO: have the logger sign the record properly
        self.prepare_data(record_name, content=payload, signer=None)


    def insert_record(self, record_event):
        if len(self.record_list) == 0:
            record_event["payload"]["prior_digest_1"] = record_event
            record_event["payload"]["prior_digest_2"] = record_event
        elif len(self.record_list) == 1:
            record_event["payload"]["prior_digest_1"] = self.record_list[-1]
            record_event["payload"]["prior_digest_2"] = self.record_list[-1]
        else:
            record_event["payload"]["prior_digest_1"] = self.record_list[-1]
            record_event["payload"]["prior_digest_2"] = self.record_list[-2]
        self.record_list.insert(len(self.record_list), record_event)


