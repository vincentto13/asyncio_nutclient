import asyncio
import re
from enum import Enum
from typing import List
import logging


def smart_split(text):
    """
    Function splits on white spaces, except for text that is qouted
    within qutation marks, or apostrophes
    """
    return re.split("""\s+(?=(?:[^'"]|'[^']*'|"[^"]*")*$)""", text)


class UpsVariableType(Enum):
    Number = "NUMBER"
    RW = "RW"
    String = "STRING"
    Enum = "ENUM"
    Range = "RANGE"


class UpsStatus(Enum):
    OnLine = "OL"
    OnBattery = "OB"
    LowBattery = "LB"
    ReplaceBattery = "RB"
    Discharge = "DISCHRG"
    Charge = "CHRG"
    CAL = "CAL"
    FSD = "FSD"


class UpsInstance:
    def __init__(self, ups: str, host: str, port: int) -> None:
        self.ups = ups
        self.host = host
        self.port = port

    def __hash__(self):
        return hash((self.ups, self.host, self.port))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return (
            self.ups == other.ups
            and self.host == other.host
            and self.port == other.port
        )

    def __repr__(self):
        return f'UpsInstance("{self.to_address()}")'

    def to_address(self) -> str:
        return f"{self.ups}@{self.host}:{self.port}"

    def get_host_port(self):
        return (self.host, self.port)

    @classmethod
    def from_address(cls, address):
        m = re.findall(r"(\w+)\@([a-zA-Z0-9_.]+)\:(\d+)", address)
        if not m or not len(m) == 1:
            return None
        data = m[0]
        if not len(data) == 3:
            return None
        return cls(data[0], data[1], int(data[2]))


class NutList(dict):
    def structured(self):
        result = {}
        for key, value in self.items():
            node = result
            for item in key.split("."):
                node.setdefault(item, {})
                node = node[item]
            node.setdefault("value", value)
        return result


class NutClient:
    def __init__(self, host, port=3493):
        self.reader = None
        self.writer = None
        self.host = host
        self.port = port

    @property
    def connected(self):
        return (self.reader is not None) and (self.writer is not None) and not self.writer.is_closing()

    async def connect(self):
        (self.reader, self.writer) = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port), timeout=5
        )

    async def _execute(self, command, response_handler):
        retries = 3
        while retries:
            try:
                self.writer.write((" ".join(command) + "\n").encode())
                await self.writer.drain()
                while True:
                    data = await asyncio.wait_for(self.reader.readline(), timeout=2)
                    if not data and not self.connected():
                        await self.connect()
                        break
                    data = smart_split(data.decode("utf-8").strip())
                    if response_handler:
                        result = response_handler.parse(data)
                        if result is not None:
                            return result
            except ConnectionRefusedError:
                raise
            except IOError:
                pass
            except asyncio.TimeoutError:
                pass
            except NutClient.CommandError as e:
                return e
            retries -= 1
        return None

    class CommandError(Exception):
        pass

    class ErrorCommandHandler:
        def parse_error(self, data):
            if data[0] == "ERR":
                raise NutClient.CommandError(data[1])

    class GenericOkCommandHandler(ErrorCommandHandler):
        def __init__(self):
            """"""

        def parse(self, data):
            self.parse_error(data)
            if data[0] == "OK":
                return True

    class GenericListCommandHandler(ErrorCommandHandler):
        def __init__(self, command):
            self.response = None
            self.command = tuple(command)

        def parse(self, data):
            self.parse_error(data)
            if data[0] == "BEGIN" and tuple(data[1:]) == self.command:
                self.response = NutList()
            elif data[0] == "END":
                if tuple(data[1:]) == self.command:
                    return self.response
            else:
                item_signature = self.command[1:]
                if tuple(data[: len(item_signature)]) == item_signature:
                    item = data[len(item_signature) :]
                    self.response[item[0]] = item[1].strip("\"'")
            return None

    class GenericGetCommandHandler(ErrorCommandHandler):
        def __init__(self, command):
            self.response = None
            self.command = tuple(command[1:])

        def parse(self, data):
            self.parse_error(data)
            if tuple(data[: len(self.command)]) == self.command:
                return [item.strip("\"'") for item in data[len(self.command) :]]

    async def list_ups(self):
        command = ["LIST", "UPS"]
        response_handler = NutClient.GenericListCommandHandler(command)
        result = await self._execute(command, response_handler)
        return result

    async def list_var(self, ups):
        command = ["LIST", "VAR", ups]
        response_handler = NutClient.GenericListCommandHandler(command)
        result = await self._execute(command, response_handler)
        return result

    async def username(self, username):
        command = ["USERNAME", username]
        response_handler = NutClient.GenericOkCommandHandler()
        result = await self._execute(command, response_handler)
        return result

    async def password(self, username):
        command = ["PASSWORD", username]
        response_handler = NutClient.GenericOkCommandHandler()
        result = await self._execute(command, response_handler)
        return result

    async def get(self, cmd, *args):
        command = ["GET", cmd.upper(), *args]
        response_handler = NutClient.GenericGetCommandHandler(command)
        result = await self._execute(command, response_handler)
        return result[0]

    async def get_status(self, ups) -> List[UpsStatus]:
        result = await self.get("VAR", ups, "ups.status")
        try:
            return [UpsStatus(item) for item in result.split(" ")]
        except:
            return []
