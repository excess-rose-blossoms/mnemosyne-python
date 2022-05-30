from enum import Enum
from typing import List
from ndn.encoding import *

# A note about names:
# Name is a class of helper functions for names; you never instantiate a Name.
# Similarly, Component is a class of functions for processing name components.
# FormalName and NonStrictName are just aliases.
# FormalName = List[BinaryStr] -- a list of name components.
# NonStrictName = Union[Iterable[Union[BinaryStr, str]], str, BinaryStr]
# NonStrictName can be several different formats, string is easiest.
# Name.normalize converts NonStrictName to FormalName.
# Record.record_name should be a FormalName.

class RecordType(Enum):
    BASE_RECORD = 0
    GENERIC_RECORD = 1
    CERTIFICATE_RECORD = 2
    REVOCATION_RECORD = 3
    GENESIS_RECORD = 4


class Record(TlvModel):

    def __init__(self,
                 record_name: NonStrictName,
                 record_type: RecordType = None,
                 data = None):
        self.record_name:FormalName = Name.normalize(record_name)
        self.record_type:RecordType = record_type
        self.data = data # TODO: figure out type for this and call constructor if necessary
        self.record_pointers:List[FormalName] = []
        self.content_item = None # TODO: figure out type for this
    
    # Get the NDN data full name of the record.
    # This is not the record's identifier.
    # The name is only generated when adding the record into the ledger.
    # This can only be used to parse a record returned from the ledger.
    def get_record_full_name(self) -> FormalName:
        if (self.data is not None):
            return self.data.get_full_name() # TODO: implement that
        return []

    # Get the record's name.
    # e.g., /<producer-prefix>/RECORD/<event-name>
    def get_record_name(self) -> FormalName:
        return self.record_name

    # Get the name of the underlying event.
    # i.e., the <event-name> in /<producer-prefix>/RECORD/<event-name>
    def get_event_name(self) -> FormalName:
        for i in range(len(self.record_name) - 1):
            if (Component.to_str(self.record_name[i]) == "RECORD"
                    or Component.to_str(self.record_name[i]) == "GENESIS_RECORD"):
                return [self.record_name[i + 1]]
        return []
    
    # TODO: figure out argument type (Block in Mnemosyne)
    # Add a new payload item into the record.
    # Should only be used in generating record before adding it to ledger.
    def set_content_item(self, content_item) -> None:
        self.content_item = content_item
    
    # TODO: figure out return type (Block in Mnemosyne)
    # Get record payload.
    def get_content_item(self):
        return self.content_item

    # Get record type.
    def get_type(self) -> RecordType:
        return self.record_type

    # TODO: implmenet self.content_item.is_valid()
    # Check if the record body is empty.
    def is_empty(self) -> bool:
        return (self.data is None
                and len(self.record_pointers) == 0
                and not self.content_item.is_valid())
    
    # Get this record's pointers to other records.
    def get_pointers_from_header(self) -> List[FormalName]:
        return self.record_pointers

    # Add a pointer to another record.
    def add_pointer(self, pointer: FormalName) -> None:
        if (self.data is not None):
            raise RuntimeError('add_pointer tried to modify an already-built record.')
        self.record_pointers.append(pointer)

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

    # TODO: figure out type of block
    def wire_encode(self, block) -> None:
        self.header_wire_encode(block)
        self.body_wire_encode(block)
    
    def header_wire_encode(self, block) -> None:
        pass

    def body_wire_encode(self, block) -> None:
        pass

