from typing import List
from ndn.encoding import Component, Name, FormalName, NonStrictName, TlvModel, BytesField, RepeatedField
import hashlib

class RecordTypes:
    RECORD_NAME = 301
    RECORD_POINTER = 302
    LOG_EVENT = 303
    RECORD_POINTER_HASH = 304

class RecordTlv(TlvModel):
    record_name = BytesField(RecordTypes.RECORD_NAME)
    record_pointers = RepeatedField(BytesField(RecordTypes.RECORD_POINTER))
    record_pointer_hashes = RepeatedField(BytesField(RecordTypes.RECORD_POINTER_HASH))
    log_event = BytesField(RecordTypes.LOG_EVENT)

class Record:

    def __init__(self,
                 record_name: NonStrictName = None,
                 producer_name: NonStrictName = None,
                 log_event: str = None,
                 event_name: FormalName = None,
                 data: bytearray = None):
        self.record_name: FormalName = None
        self.record_pointers: List[FormalName] = []
        self.record_pointer_hashes = []
        self.log_event: str = None
        self.record_tlv: RecordTlv = None
        if (record_name is not None):
            # Create record with the name as provided.
            # Used for genesis records.
            self.record_name: FormalName = Name.normalize(record_name)
        elif (producer_name is not None
              and log_event is not None
              and event_name is not None):
            # Create record from producer name + event
            # Used when generating our own records.
            self.record_name: FormalName = (
                Name.normalize(producer_name + "/RECORD/") + event_name)
            self.log_event = log_event
        elif (data is not None):
            # Create record from raw data.
            # Used when creating a Record to represent a received Record.
            self.record_tlv: RecordTlv = RecordTlv.parse(data)
            self.record_name = Name.from_bytes(self.record_tlv.record_name)
            for ptr in self.record_tlv.record_pointers:
                self.record_pointers.append(Name.from_bytes(ptr))
            for ptr_hash in self.record_tlv.record_pointer_hashes:
                self.record_pointer_hashes.append(ptr_hash.tobytes().decode())
            self.log_event = self.record_tlv.log_event.tobytes().decode()
        else:
            raise RuntimeError('Invalid call to Record constructor')
    
    # This is commented out because full names are currently no
    # different than NDN record names, because names don't contain
    # hashes yet.
    # Get the NDN data full name of the record.
    # This is not the record's identifier.
    # The name is only generated when adding the record into the ledger.
    # This can only be used to parse a record returned from the ledger.
    # def get_record_full_name(self) -> FormalName:
    #     if (self.record_tlv is not None):
    #         return self.record_tlv.get_full_name()
    #     return []
    def get_record_hash(self):
        record_str = Name.to_str(self.get_record_name())
        if (len(self.record_pointers) >= 1):
            record_str += (
                Name.to_str(self.record_pointers[0])
                + self.record_pointer_hashes[0])
        if (len(self.record_pointers) >= 2):
            record_str += (
                Name.to_str(self.record_pointers[1])
                + self.record_pointer_hashes[1])
        record_str += self.get_log_event()

        return hashlib.sha256(record_str.encode()).hexdigest()

    # Get the record's name.
    # e.g., /<producer-prefix>/RECORD/<event-name>
    def get_record_name(self) -> FormalName:
        return self.record_name
    def get_record_name_str(self) -> str:
        return Name.to_str(self.record_name)

    # Get the name of the underlying event.
    # i.e., the <event-name> in /<producer-prefix>/RECORD/<event-name>
    def get_event_name(self) -> FormalName:
        for i in range(len(self.record_name) - 1):
            if (Component.to_str(self.record_name[i]) == "GENESIS_RECORD"
                    or Component.to_str(self.record_name[i]) == "RECORD"):
                return [self.record_name[i + 1]]
        return []

    # Add the log event to the record.
    # Should only be used in generating record before adding it to ledger.
    def set_log_event(self, log_event: str) -> None:
        self.log_event = log_event

    # Get record payload.
    def get_log_event(self) -> str:
        return self.log_event

    # Get this record's pointers to other records.
    def get_pointers_from_header(self) -> List[FormalName]:
        return self.record_pointers

    def get_pointer_hashes_from_header(self) -> List:
        return self.record_pointer_hashes

    # Add a pointer to another record.
    def add_pointer(self, record_pointer: FormalName, record_hash) -> None:
        if (self.record_tlv is not None):
            raise RuntimeError('add_pointer tried to modify an already-built record.')
        self.record_pointers.append(record_pointer)
        self.record_pointer_hashes.append(record_hash)

    # Validate the pointers in the header.
    def check_pointer_count(self, num_pointers: int) -> None:
        pointers = self.get_pointers_from_header()
        if (len(pointers) != num_pointers):
            raise RuntimeError('Incorrect number of pointers in record.')

        pointers_copy = []
        for pointer in pointers:
            if (pointer in pointers_copy):
                raise RuntimeError('Duplicate pointer detected.')
            pointers_copy.append(pointer)

    def get_producer_prefix(self) -> FormalName:
        for i in range(len(self.record_name - 1)):
            if (Component.to_str(self.record_name[i]) == "GENESIS_RECORD"
                    or Component.to_str(self.record_name[i]) == "RECORD"):
                return self.record_name[:i]
        return []

    def wire_encode(self) -> bytearray:
        self.record_tlv = RecordTlv()
        self.record_tlv.record_name = Name.to_bytes(self.record_name)
        for ptr in self.record_pointers:
            self.record_tlv.record_pointers.append(Name.to_bytes(ptr))
        for ptr_hash in self.record_pointer_hashes:
            self.record_tlv.record_pointer_hashes.append(ptr_hash.encode())
        self.record_tlv.log_event = self.log_event.encode()
        return self.record_tlv.encode()

    def is_genesis_record(self) -> bool:
        for i in range(len(self.record_name) - 1):
            if (Component.to_str(self.record_name[i]) == "RECORD"):
                return False
            if (Component.to_str(self.record_name[i]) == "GENESIS_RECORD"):
                return True
        return False

    # Print all info for debugging
    def print(self) -> None:
        print("Record:\t" + Name.to_str(self.get_record_name()))
        print("Link1:\t" + Name.to_str(self.record_pointers[0]))
        print("Link1-hash:\t" + self.record_pointer_hashes[0])
        print("Link2:\t" + Name.to_str(self.record_pointers[1]))
        print("Link2-hash:\t" + self.record_pointer_hashes[1])
        print("Log event:\t" + self.get_log_event())
        print("Encoded:")
        if (self.record_tlv is not None):
            print(self.record_tlv.encode())
        else:
            print(None)
        print('')

class GenesisRecord(Record):
    def __init__(self, number: int):
        super().__init__(record_name="/mnemosyne/GENESIS_RECORD/" + str(number))
        self.set_log_event("")
