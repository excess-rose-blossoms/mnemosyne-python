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

class Program:
    def __init__(self) -> None:
        self.group_prefix = "/svs/mnemosyne/log_events"
        self.node_id = "producer_1"
        self.interval = 1
        self.svs:SVSync = SVSync(app, Name.from_str(self.group_prefix), Name.from_str(self.node_id), self.missing_callback)
        print(f'PRODUCER STARTED! | GROUP PREFIX: {self.group_prefix} | NODE ID: {self.node_id} |')
    async def run(self) -> None:
        num:int = 0
        while 1:
            num = num+1
            try:
                print("produced log event: "+str(num))
                self.svs.publishData(str(num).encode())
            except KeyboardInterrupt:
                sys.exit()
            await aio.sleep(self.interval)
    def missing_callback(self, missing_list:List[MissingData]) -> None:
        pass

async def start() -> None:
    prog = Program()
    await prog.run()

def main() -> int:
    try:
        app.run_forever(after_start=start())
    except (FileNotFoundError, ConnectionRefusedError):
        print('Error: could not connect to NFD for SVS.')

    return 0

if __name__ == "__main__":
    sys.exit(main())
