import asyncio as aio
import logging
import sys
import time
import ast
from argparse import ArgumentParser, SUPPRESS
from typing import List, Optional
# NDN Imports
from ndn.app import NDNApp
from ndn.encoding import Name
# Custom Imports
sys.path.insert(0,'.')
from ndn.svs import SVSync, SVSyncLogger, MissingData

app = NDNApp()

def parse_cmd_args() -> dict:
    # Command Line Parser
    parser = ArgumentParser(add_help=False,description="Logger node receiving log events and putting them into a DAG as records.")
    requiredArgs = parser.add_argument_group("required arguments")
    optionalArgs = parser.add_argument_group("optional arguments")
    informationArgs = parser.add_argument_group("information arguments")
    # Adding all Command Line Arguments
    requiredArgs.add_argument("-n", "--nodename",action="store",dest="node_name",required=True,help="id of this node in svs")
    optionalArgs.add_argument("-v","--verbose",action="store_true",dest="verbose",default=False,required=False,help="when set, svsync info is displayed as well")
    informationArgs.add_argument("-h","--help",action="help",default=SUPPRESS,help="show this help message and exit")
    # Getting all Arguments
    argvars = parser.parse_args()
    args = {}
    args["node_id"] = argvars.node_name
    args["verbose"] = argvars.verbose
    return args

# each entry is stored like so: {record_name: [link_1, link_2]}
class RecordStorage:
    def __init__(self):
        self.records_list = {}
        self.tail_records = {}

    def store_record(self, new_record):
        self.records_list.update(new_record)

    def pop_tail_record(self):
        if (len(self.tail_records) > 0):
            name = list(self.tail_records.keys())[0]
            return self.tail_records.pop(name)
        return None
        
    def get_record(self, record_name):
        if record_name in self.records_list:
            return self.records_list[record_name]
        return None

record_storage = RecordStorage()

class Consumer:
    def __init__(self, args:dict) -> None:
        self.args = args
        self.record_changes = []
        self.interest_queue = []
        # log_events group related (communication between producer and loggers)
        self.log_events_group_prefix = "/svs/mnemosyne/log_events"
        self.svs_log_events:SVSync = SVSync(app, Name.from_str(self.log_events_group_prefix), Name.from_str(self.args["node_id"]), self.log_events_missing_callback)
        # records_group related (communication between loggers)
        self.records_group_prefix = "/svs/mnemosyne/records"
        self.svs_records:SVSync = SVSync(app, Name.from_str(self.records_group_prefix), Name.from_str(self.args["node_id"]), self.records_missing_callback)
        print(f'CONSUMER STARTED! | LOG GROUP PREFIX: {self.log_events_group_prefix} | RECORDS GROUP PREFIX {self.records_group_prefix} | NODE ID: {self.args["node_id"]} |')

    async def run(self) -> None:
        if (len(self.interest_queue) > 0):
            try:
                data_name, meta_info, content = await app.express_interest(
                    # Interest Name
                    '/mnemosyne/record_interest' + self.interest_queue.pop(),
                    must_be_fresh=True,
                    can_be_prefix=False,
                    lifetime=6000)
                record_storage.store_record({Name.to_str(data_name):bytes(content)})
            except InterestNack as e:
                # A NACK is received
                print(f'Nacked with reason={e.reason}')
            except InterestTimeout:
                # Interest times out
                print(f'Timeout')
            except InterestCanceled:
                # Connection to NFD is broken
                print(f'Canceled')
            except ValidationFailure:
                # Validation failure
                print(f'Data failed to validate')

    @app.route('/mnemosyne/record_interest')
    def on_interest(name, interest_param, application_param):
        retrieved_record = record_storage.get_record(name)
        if retrieved_record:
            app.put_data(name, content=retrieved_record, freshness_period=10000)

    # Given a log event, create and return an NDN record packet.
    # TODO: This is a temporary implementation. Should actually convert the stuff to packets.
    def create_record(self, log_event):
        prior_records = [tail for tail in [record_storage.pop_tail_record(), record_storage.pop_tail_record()] if tail]
        # Log the tail records removed
        for prior_record in prior_records:
            self.record_changes.append("DEL-TAIL " + prior_record)
        return {str(log_event):prior_records}

    # Creates and stores a record. Notes down the record changes to be published by SVS.
    def receive_log_event(self, content_str):
        new_record = self.create_record(content_str.decode())
        record_storage.store_record(new_record)
        self.record_changes.append("ADD-REC " + content_str.decode())
        self.publish_record_changes()

    def publish_record_changes(self):
        for change in self.record_changes:
            self.svs_records.publishData(str(change).encode())
        self.record_changes = []

    def receive_record_changes(self, record_changes):
        record_change_list = ast.literal_eval(record_changes)
        for record_change in record_change_list:
            split_change = record_change.split(" ")
            if split_change[0] == "ADD-REC":
                new_record = self.interest_queue.append(split_change[1])
            elif split_change[0] == "DEL-TAIL":
                record_storage.pop_tail_record(split_change[1])
        return

    def log_events_missing_callback(self, missing_list:List[MissingData]) -> None:
        aio.ensure_future(self.log_events_on_missing_data(missing_list))

    async def log_events_on_missing_data(self, missing_list:List[MissingData]) -> None:
        for i in missing_list:
            while i.lowSeqno <= i.highSeqno:
                content_str:Optional[bytes] = await self.svs_log_events.fetchData(Name.from_str(i.nid), i.lowSeqno, 2)
                if content_str: # RELEVANT STUFF HERE
                    self.receive_log_event(content_str)
                i.lowSeqno = i.lowSeqno + 1

    def records_missing_callback(self, missing_list:List[MissingData]) -> None:
        aio.ensure_future(self.records_on_missing_data(missing_list))

    async def records_on_missing_data(self, missing_list:List[MissingData]) -> None:
        for i in missing_list:
            while i.lowSeqno <= i.highSeqno:
                content_str:Optional[bytes] = await self.svs_records.fetchData(Name.from_str(i.nid), i.lowSeqno, 2)
                if content_str: # RELEVANT STUFF HERE
                    self.receive_record_changes(content_str.decode())
                i.lowSeqno = i.lowSeqno + 1

async def start(args:dict) -> None:
    cons = Consumer(args)
    await cons.run()

def main() -> int:
    args = parse_cmd_args()
    args["node_id"] = Name.to_str(Name.from_str(args["node_id"]))

    SVSyncLogger.config(True if args["verbose"] else False, None, logging.INFO)

    try:
        app.run_forever(after_start=start(args))
    except (FileNotFoundError, ConnectionRefusedError):
        print('Error: could not connect to NFD for SVS.')

    return 0

if __name__ == "__main__":
    sys.exit(main())
