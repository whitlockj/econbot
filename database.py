import asyncio
import aiosqlite
import logging
import os

PATH = os.path.abspath(os.getcwd()) + "/database.db"


logger = logging.getLogger("custom")

async def load():
    aiosqlite.connect(PATH)
    

async def write(sql_command: str,
                *params
            ) -> bool:

    async with aiosqlite.connect(PATH) as conn:
        conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = await conn.cursor()
        try:
            await cur.execute(sql_command, params)
            await conn.commit()
            return True
        except Exception as e:
            logger.exception(e)
            return False

async def read(sql_command: str,
               *params,
               multiple: bool = False,
               dict_cursor: bool = True
            ) -> (list | dict | tuple):
    """
    returns: multiple -> list [ ]
    returns: dict_cursor -> dict [ str, Any ]
    returns: neither -> tuple ( Any )
    """
    async with aiosqlite.connect(PATH) as conn:
        if dict_cursor:
            conn.row_factory = lambda col, row: dict(zip([_col[0] for _col in col.description], row))
            
        cur = await conn.cursor()

        try:
            await cur.execute(sql_command, params)
            if multiple:
                data: list[tuple | dict] = await cur.fetchall()
            else:
                data: tuple | dict = await cur.fetchone()
        except Exception as e:
            logger.exception(e)
            return None

    return data

if __name__ == "__main__":
    async def main():
        await load()
        while True:
            try:
                action = input("\n\nWrite? (Y): ").upper()
                sql = input("sql query: ")
                

                if action == "Y":
                    
                    args = input("args: ")
                    if "," in args:
                        args = [arg.strip() for arg in args.split(",")]
                        print(args)   
                        await write(sql, *args)
                        
                    else:
                        await write(sql)
                        
                else:
                    print(await read(sql, multiple=True, dict_cursor=True))
                    
            except Exception as e:
                raise e
    asyncio.run(main())
