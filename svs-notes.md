### Create SVSync object

Constructor API
```
SVSync(Face, Name syncPrefix, Name nodePrefix, UpdateCallback, SecurityOptions)
```

example:
```
self.svs:SVSync = SVSync(app, Name.from_str(self.args["group_prefix"]), Name.from_str(self.args["node_id"]), self.missing_callback)
```

where self.missing_callback refers to:

```
def missing_callback(self, missing_list:List[MissingData]) -> None:
        aio.ensure_future(self.on_missing_data(missing_list))
```
(called when there's an update and updates the missing_list data structure)

### Request data
this requests the missing data when there is some

```
async def on_missing_data(self, missing_list:List[MissingData]) -> None:
        for i in missing_list:
            while i.lowSeqno <= i.highSeqno:
                content_str:Optional[bytes] = await self.svs.fetchData(Name.from_str(i.nid), i.lowSeqno, 2)
                if content_str:
                    output_str:str = i.nid + ": " + content_str.decode()
                    sys.stdout.write("\033[K")
                    sys.stdout.flush()
                    print(output_str)
                i.lowSeqno = i.lowSeqno + 1
```

### Publish data
```
self.svs.publishData(str(num).encode())
```