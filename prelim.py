from ndn.app import NDNApp
from ndn.encoding.name import Name

# basic building block code for the resource records
class Logger(NDNApp):
    def __init__(self, logger_ID, record_dag):
        NDNApp.__init__(face=None, keychain=None)
        self.logger_ID = logger_ID # TODO: Find a sensible way of assigning a logger ID
        self.record_dag = record_dag # TODO: remove this later -- DAG should be obtained from NDN SVS Sync
        return
    
    def receive_event(self, log_event):
        # TODO: set random timer
        # Case: Timer goes off
            #Authenticate event
            self.create_record(log_event)
            #Poll SVS??
            #Publish record to SVS
            #Insert record into DAG
        

    def create_record(self, log_event):
        # SVS event
        record_name = Name.from_str(self.logger_ID + "/" + "RECORD" + log_event) # TODO: replace log_event.id with an actual identifier from the log event received
        # TODO: assign prior record digests based on the tails + turn them into digests
        # TODO: conditional logic depending on whether two tails are even available
        payload = {"log_event": log_event, "prior_digest_1": None, "prior_digest_2": None}
        # TODO: have the logger sign the record properly
        self.prepare_data(record_name, content=payload, signer=None)