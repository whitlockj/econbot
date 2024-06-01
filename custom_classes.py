import asyncio
from functools import lru_cache
from database import read, write
from typing import Any, Callable
from ast import literal_eval


class _ListItemWithTTL:
    def __init__(self, loop: asyncio.BaseEventLoop, remove_func, value, ttl: int = 600) -> None:
        self.value = value
        
        if ttl <= 0:
            return
        
        loop.create_task(self.__remove(ttl))
        self.remove_func = remove_func
    
    async def __remove(self, ttl: int):
        await asyncio.sleep(ttl)
        self.remove_func(self.value)

    def __str__(self) -> str:
        return str(self.value)
    
    def __repr__(self) -> str:
        return repr(self.value)


class ListWithTTL:
    def __init__(self, *values, loop: asyncio.BaseEventLoop | None = None, default_ttl: int = 600) -> None:

        if loop is None:
            self.loop = asyncio.get_event_loop()
        else:
            self.loop = loop

        self.ttl = default_ttl
        self.__list = [_ListItemWithTTL(self.loop, self.delete_item, value, self.ttl) for value in values]

    def __getitem__(self, index: int):
        return self.__list[index].value
    
    def __setitem__(self, index: int, value):
        self.__list[index].value = value
    
    def append(self, *values, ttl: int | None = None):
        if ttl is None:
            ttl = self.ttl
        
        self.__list.extend(_ListItemWithTTL(self.loop, self.delete_item, value, ttl) for value in values)
    
    def delete_item(self, value):
        for i, val in enumerate(self.__list):
            if value == val.value:
                self.__list.pop(i)
                break
        else:
            raise ValueError(f"'{value}' not in list")

    @lru_cache
    def __iter__(self):
        return iter(item.value for item in self.__list)
    
    def __len__(self) -> int:
        return len(self.__list)
    
    @lru_cache
    def __contains__(self, value):

        for item in self.__list:
            if value == item.value:
                return True
            
        else:
            return False
        
    def __str__(self) -> str:
        return str(self.__list)

class CustomDict:
    def __init__(self, loop: asyncio.BaseEventLoop, db_table: str, schema: dict[str, Callable]):
        self.loop = loop
        self.db_table = db_table
        self.schema = schema
        self.dict = dict(zip(self.schema.keys(), [None] * len(self.schema)))
        self.old_dict = dict(zip(self.schema.keys(), [None] * len(self.schema)))
        self.loop.create_task(self.__load())
        self.loop.create_task(self.__periodic_save())

    async def __load(self) -> None:
        data: list[dict[str, Any]] = await read(f"SELECT * FROM {self.db_table}", multiple=True, dict_cursor=True)
        
        if data is None:
            return

        for db_row in data: # {"data": "value", "data2": "1"}
            for db_key, v in db_row.items(): # data2, 1
                
                if db_key in self.schema:
                    
                    if self.schema[db_key] in [set, tuple, dict, list, None, bool]:
                        self.dict[db_key] = literal_eval(v)
                
                    else:
                        self.dict[db_key] = self.schema[db_key](v) # data2, int(1)
                        
                else:
                    raise ValueError(f"Key '{db_key}' not in schema")
            
    async def __write(self):
        if len(self.dict) == 0:
            return

        for key, value in self.dict.items():
            if self.old_dict[key] != value:
                await write(f"INSERT INTO {self.db_table} ({key}) VALUES (?) ON DUPLICATE KEY UPDATE {key}=?", value, value)

    async def __periodic_save(self):
        while True:
            await asyncio.sleep(600)
            await self.__write()

    def __getitem__(self, key: str) -> str:
        return self.dict[key]

    def __setitem__(self, key: str, value: str):
        if key not in self.schema:
            raise ValueError(f"Key '{key}' not in schema")
        self.dict[key] = value

    def __delitem__(self, key: str):
        del self.dict[key]

    def __iter__(self):
        return iter(self.dict)

    def __len__(self):
        return len(self.dict)

    def __repr__(self):
        return repr(self.dict)

    def __str__(self):
        return str(self.dict)

    def __contains__(self, key: str) -> bool:
        return key in self.schema.keys()

    def keys(self):
        return self.schema.keys()

    def values(self):
        return self.dict.values()

    def items(self):
        return self.dict.items()

    def get(self, key: str, default=None):
        return self.dict.get(key, default)

    def pop(self, key: str, default=None):
        return self.dict.pop(key, default)

    def clear(self):
        self.dict.clear()

    def copy(self):
        return self.dict.copy()

    def setdefault(self, key: str, default=None):
        return self.dict.setdefault(key, default)

    def popitem(self):
        return self.dict.popitem()

    def fromkeys(self, keys: list[str], value=None):
        return self.dict.fromkeys(keys, value)
