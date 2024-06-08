import asyncio
from functools import lru_cache
import database as db
import typing as t
from ast import literal_eval
import copy

T = t.TypeVar("T")

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

class DatabaseTable:

    def __init__(self, loop: asyncio.BaseEventLoop, db_table: str, schema: tuple[t.LiteralString, type[int | str], dict[str, type[t.Any]]], save_interval: int = 1200):
        """
        :param:`schema`: ("pkey", `type[primay key]`, { `"some string"`: type[str], `"some integer"`: type[int] } )
        """
        self.loop = loop
        self.save_interval = int(save_interval)
        self.db_table = db_table
        self.schema: tuple[t.Callable, dict[str, type[t.Any]]] = schema
        self.pkey_col_name = schema[0]
        self.pkey_type: t.Callable = schema[1]
        self.dict_schema: dict[str, type[t.Any]] = schema[2]
        self.default_dict = {}
            

        for k, v in self.dict_schema.items():
            if not isinstance(v, type):
                raise ValueError(f"Schema value '{v}' must be a type.")

            if not isinstance(k, str):
                raise ValueError(f"Schema key '{k}' must be a string.")

            if v is None:
                self.default_dict[k] = None
                
            elif v == str:
                self.default_dict[k] = "N/A"
            else:
                self.default_dict[k] = v()

            
        
        self.dict: dict[self.pkey_type, dict[str, t.Any]] = {} # {primary key: {"some string": type[str], "some integer": type[int]}}
        self.old_dict: dict[self.pkey_type, dict[str, t.Any]] = {}
        self.loaded = asyncio.Event()
        self.loop.create_task(self.__load())
        self.loop.create_task(self.__periodic_save())

    def type_to_sql(v: type | None) -> t.Literal["INTEGER", "REAL", "BOOLEAN", "TEXT"]:
        if v is None:
            x = "TEXT"
            return x

        match v():
            case int():
                x = "INTEGER"
            case float():
                x = "REAL"
            case bool():
                x = "BOOLEAN"
            case _:
                x = "TEXT"
        
        return x

    async def __load(self) -> None:
        if self.loaded.is_set():
           return 
        
        await db.load()
        string = ""
        for k, v in self.dict_schema.items():
            x = self.type_to_sql(v)
            string += f"{k} {x}, "
        
        string = string.strip().removesuffix(',')

        success = await db.write(f"CREATE TABLE IF NOT EXISTS {self.db_table} ( {self.pkey_col_name} {self.type_to_sql(self.pkey_type)} PRIMARY KEY, {string})")
        if not success:
            raise ValueError("Failed to create table.")
        data: list[dict[str, t.Any]] = await db.read(f"SELECT * FROM {self.db_table}", multiple=True, dict_cursor=True)
        if data is None:
            return
        
        if isinstance(data, bool):
            print("query ran into error:")
            return

        for db_row in data: # {"data": "value", "data2": "1"}
            primary_key = db_row[self.pkey_col_name]
            self.dict[primary_key] = {}
            
            for data_key, v in db_row.items(): # "data2", "1"

                self.dict[primary_key][data_key] = self.converter(primary_key, data_key, v)

        self.old_dict = copy.deepcopy(self.dict)

        self.loaded.set()

    def py_to_sql(self, v: t.Any) -> (str | int):
        if type(v) in [set, tuple, dict, list, bool]:
            return str(v)
        elif v is None:
            return "NULL"
        else:
            return v
        
    def converter(self, pkey, data_key: str, v: T) -> T:
        if data_key in self.dict_schema:

            if self.dict_schema[data_key] in [set, tuple, dict, list, None, bool]:
                
                if isinstance(v, self.dict_schema[data_key]):
                    return v
                
                result = literal_eval(v)

                if not isinstance(result, self.dict_schema[data_key]):
                    raise ValueError(f"Value '{v}' is not of type '{self.dict_schema[data_key]}'")
                
                return result

            else:
                try:
                    return self.dict_schema[data_key](v) # "data2", int(1)
                except:
                    
                    raise ValueError(f'{self.pkey_col_name}: {pkey}', f"'{v}' is not of type[{self.dict_schema[data_key]}], required by the '{data_key}' column")

        else:
            if data_key != self.pkey_col_name:
                raise ValueError(f"Key '{data_key}' not in dict_schema")

    async def save(self):
        if not self.loaded.is_set():
            await self.loaded.wait()
            
        if (len(self.dict) == 0) or (self.dict == self.old_dict):
            return

        for primary_key, data in self.dict.items():

            try:
                x = self.old_dict[primary_key]
            except KeyError:
                
                for k, v in data.items():
                    data[k] = self.converter(primary_key, k, v)
                
                q_marks = ""
                q_marks += "?," * (len(data)+1)
                q_marks = q_marks.strip().removesuffix(",")

                keys = str(tuple([self.pkey_col_name, *data.keys()])).replace("'", "")
                values = [primary_key, *[self.py_to_sql(x) for x in data.values()]]
                await db.write(f"INSERT INTO {self.db_table} {keys} VALUES ({q_marks})", *values)
                print(f"inserted {primary_key}")

                continue

            if self.old_dict[primary_key] != data:
                temp_dict = {}

                for col_name, value in data.items():
                    if value != self.old_dict[primary_key][col_name]:
                        temp_dict[col_name] = value


                if len(temp_dict) > 0:
                    values = []
                    string = ""

                    for k, v in temp_dict.items():
                        values.append(v)
                        string += f"{k} = ?, "

                    string = string.strip().removesuffix(",")
                    await db.write(f"UPDATE {self.db_table} SET {string} WHERE {self.pkey_col_name} = ?", *values, primary_key)
                    
        self.old_dict = copy.deepcopy(self.dict)
                

    async def __periodic_save(self):
        if not self.loaded.is_set():
            await self.loaded.wait()
        while True:
            await asyncio.sleep(self.save_interval)
            await self.save()

    def __getitem__(self, key: str) -> str:
        try:
            return self.dict[key]
        except KeyError:
            self.dict[key] = self.default_dict
            return self.dict[key]

    def __setitem__(self, key: str, value: dict):
        if not isinstance(value, dict):
            raise ValueError("Value must be a dictionary.")
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
        return key in self.dict.keys()

    def keys(self):
        return self.dict.keys()
    
    def values(self):
        return self.dict.values()

    def items(self):
        return self.dict.items()

    def get(self, key: str | int, default=None):
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