import asyncio as aio
import logging
import sys
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

class Logger:
    def __init__(self, args:dict) -> None:
        self.args = args
        # log_events group related (communication between producer and loggers)
        self.log_events_group_prefix = "/svs/mnemosyne/log_events"
        self.svs_log_events:SVSync = SVSync(app, Name.from_str(self.log_events_group_prefix), Name.from_str(self.args["node_id"]), self.log_events_missing_callback)
        # records_group related (communication between loggers)
        self.records_group_prefix = "/svs/mnemosyne/records"
        self.svs_records:SVSync = SVSync(app, Name.from_str(self.records_group_prefix), Name.from_str(self.args["node_id"]), self.records_missing_callback)
        print(f'CONSUMER STARTED! | LOG GROUP PREFIX: {self.log_events_group_prefix} | RECORDS GROUP PREFIX {self.records_group_prefix} | NODE ID: {self.args["node_id"]} |')

    # Given a log event, create and return an NDN record packet.
    # TODO: This is a temporary implementation. Should actually convert the stuff to packets.
    def create_record(self, log_event):
        prior_records = [tail for tail in [record_storage.pop_tail_record(), record_storage.pop_tail_record()] if tail]
        return {str(log_event):prior_records}

    def log_events_missing_callback(self, missing_list:List[MissingData]) -> None:
        aio.ensure_future(self.on_missing_events(missing_list))

    async def on_missing_events(self, missing_list:List[MissingData]) -> None:
        for i in missing_list:
            while i.lowSeqno <= i.highSeqno:
                content_str:Optional[bytes] = await self.svs_log_events.fetchData(Name.from_str(i.nid), i.lowSeqno, 2)
                if content_str:
                    self.receive_log_event(content_str)
                    # if ((self.args["node_id"] == "/even" and int(content_str.decode()) % 2 == 0)
                    #     or (self.args["node_id"] == "/odd" and int(content_str.decode()) % 2 == 1)):
                    #     self.receive_log_event(content_str)

                i.lowSeqno = i.lowSeqno + 1

    # Creates and stores a record. Notes down the record changes to be published by SVS.
    def receive_log_event(self, content_str):
        # TODO: authenticate log event
        new_record = self.create_record(content_str.decode())
        # TODO: update tails list
        record_storage.store_record(new_record)
        # TODO: change this to send the actual record
        self.svs_records.publishData("ADD-REC ".encode() + content_str)

    def records_missing_callback(self, missing_list:List[MissingData]) -> None:
        aio.ensure_future(self.on_missing_records(missing_list))

    async def on_missing_records(self, missing_list:List[MissingData]) -> None:
        for i in missing_list:
            while i.lowSeqno <= i.highSeqno:
                content_str:Optional[bytes] = await self.svs_records.fetchData(Name.from_str(i.nid), i.lowSeqno, 2)
                if content_str:
                    self.receive_records(content_str.decode())
                i.lowSeqno = i.lowSeqno + 1

    def receive_records(self, record_changes):
        # TODO: parse record
        # TODO: verify record by tracing back to root
        # TODO: save record
        print(record_changes)


async def start(args:dict) -> None:
    logger = Logger(args)

def main() -> int:
    args = parse_cmd_args()
    args["node_id"] = Name.to_str(Name.from_str(args["node_id"]))

    SVSyncLogger.config(True if args["verbose"] else False, None, logging.INFO)

    try:
        app.run_forever(after_start=start(args))
    except (FileNotFoundError, ConnectionRefusedError):
        print('Error: could not connect to NFD for SVS.')
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
