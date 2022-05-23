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
from src.ndn.svs import SVSync, SVSyncLogger, MissingData

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

class Consumer:
    def __init__(self, args:dict) -> None:
        self.args = args
        self.records_list = []
        self.tails_list = []
        # log_events group related (communication between producer and loggers)
        self.log_events_group_prefix = "/svs/mnemosyne/log_events"
        self.svs_log_events:SVSync = SVSync(app, Name.from_str(self.log_events_group_prefix), Name.from_str(self.args["node_id"]), self.log_events_missing_callback)
        # records_group related (communication between loggers)
        self.records_group_prefix = "/svs/mnemosyne/records"
        self.svs_records:SVSync = SVSync(app, Name.from_str(self.records_group_prefix), Name.from_str(self.args["node_id"]), self.records_missing_callback)
        print(f'CONSUMER STARTED! | LOG GROUP PREFIX: {self.log_events_group_prefix} | RECORDS GROUP PREFIX {self.records_group_prefix} | NODE ID: {self.args["node_id"]} |')
    
    # TODO: remove this later -- this is a tempoorary measure to let consumers simulate receiving events from a non-existent producer
    async def run(self) -> None:
        counter = 1
        while True:
            try:
                if (self.args["node_id"] == "/even" and counter % 2 == 0):
                    record_changes = self.store_record(str(counter).encode())
                    self.publish_record_changes(record_changes)
                elif (self.args["node_id"] == "/odd" and counter % 2 != 0):
                    record_changes = self.store_record(str(counter).encode())
                    self.publish_record_changes(record_changes)
                counter += 1
            except KeyboardInterrupt:
                sys.exit()
            await aio.sleep(1)

    # Given a log event, create and return an NDN record packet.
    # TODO: This is a temporary implementation. Should actually convert the stuff to packets
    def create_record(self, log_event, record_1, record_2):
        return {"log":log_event, "r1": record_1, "r2": record_2}
    
    # Takes care of the behavior of storing the relevant record to the tails and records lists.
    # Returns an object with information about changes in records
    def store_record(self, content_str):
        # Create and store record
        record_1 = self.tails_list.pop() if (len(self.tails_list) > 0) else None
        record_2 = self.tails_list.pop() if (len(self.tails_list) > 0) else None
        new_record = self.create_record(content_str.decode(), (record_1["log"] if record_1 else None), (record_2["log"] if record_2 else None))
        self.records_list.append(new_record)
        self.tails_list.append(new_record)
        # Note and return actions taken
        record_changes = []
        record_changes.append("ADD-REC" + " | " + str(new_record))
        record_changes.append("ADD-TAIL" + " | " + str(new_record))
        if (record_1):
            record_changes.append("DEL-TAIL" + " | " + str(record_1))
        if (record_2):
            record_changes.append("DEL-TAIL" + " | " + str(record_2))
        return record_changes

    def publish_record_changes(self, record_changes):
        for change in record_changes:
            self.svs_records.publishData(str(change).encode())

    # Parse an input list of record changes and make changes to the records accordingly
    def update_records(self, record_changes_str):
        split_change = record_changes_str.split(' | ')
        print(split_change)
        if split_change[0] == "ADD-REC":
            self.records_list.append(ast.literal_eval(split_change[1]))
        elif split_change[0] == "ADD-TAIL":
            self.tails_list.append(ast.literal_eval(split_change[1]))
        elif split_change[0] == "DEL-TAIL":
            try:
                self.tails_list.remove(ast.literal_eval(split_change[1]))
            except ValueError:
                pass
        return

    def log_events_missing_callback(self, missing_list:List[MissingData]) -> None:
        aio.ensure_future(self.log_events_on_missing_data(missing_list))

    async def log_events_on_missing_data(self, missing_list:List[MissingData]) -> None:
        for i in missing_list:
            while i.lowSeqno <= i.highSeqno:
                content_str:Optional[bytes] = await self.svs_log_events.fetchData(Name.from_str(i.nid), i.lowSeqno, 2)
                if content_str:
                    self.store_record(content_str)
                i.lowSeqno = i.lowSeqno + 1

    def records_missing_callback(self, missing_list:List[MissingData]) -> None:
        aio.ensure_future(self.records_on_missing_data(missing_list))

    async def records_on_missing_data(self, missing_list:List[MissingData]) -> None:
        for i in missing_list:
            while i.lowSeqno <= i.highSeqno:
                content_str:Optional[bytes] = await self.svs_records.fetchData(Name.from_str(i.nid), i.lowSeqno, 2)
                if content_str:
                    print("--------------")
                    print("-BEFORE RECORD UPDATE-")
                    print("RECORDS: " + str(self.records_list))
                    print("TAILS: " + str(self.tails_list))
                    self.update_records(content_str.decode())
                    print("-AFTER RECORD UPDATE-")
                    print("RECORDS: " + str(self.records_list))
                    print("TAILS: " + str(self.tails_list))
                    print("--------------")
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
