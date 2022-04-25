import asyncio
import re
from enum import Enum
import logging


def smart_split(text):
    """
    Function splits on white spaces, except for text that is qouted
    within qutation marks, or apostrophes
    """
    return re.split("""\s+(?=(?:[^'"]|'[^']*'|"[^"]*")*$)""", text)


class UpsStatus(Enum):
    OnLine = "OL"
    OnBattery = "OB"
    LowBattery = "LB"
    ReplaceBattery = "RB"
    CAL = "CAL"
    FSD = "FSD"


class NutClient:
    def __init__(self, host, port=3493):
        self.reader = None
        self.writer = None
        self.host = host
        self.port = port

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
                    if not data:
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
        def __init__(self, command, item_handler=None):
            self.response = None
            self.command = tuple(command)
            self.item_handler = item_handler

        def parse(self, data):
            self.parse_error(data)
            if data[0] == "BEGIN" and tuple(data[1:]) == self.command:
                self.response = {}
            elif data[0] == "END":
                if tuple(data[1:]) == self.command:
                    return self.response
            elif self.item_handler:
                item_signature = self.command[1:]
                if tuple(data[: len(item_signature)]) == item_signature:
                    self.item_handler(self.response, data[len(item_signature) :])
            return None

    class GenericGetCommandHandler(ErrorCommandHandler):
        def __init__(self, command):
            self.response = None
            self.command = tuple(command[1:])

        def parse(self, data):
            self.parse_error(data)
            if tuple(data[: len(self.command)]) == self.command:
                return data[len(self.command) :]

    @staticmethod
    def response_ups_handler(response, data):
        response[data[0]] = {"Description": data[1]}

    @staticmethod
    def response_var_handler(response, data):
        node = response
        for item in data[0].split("."):
            node.setdefault(item, {})
            node = node[item]
        node.setdefault("value", data[1])

    async def list_ups(self):
        command = ["LIST", "UPS"]
        response_handler = NutClient.GenericListCommandHandler(
            command, NutClient.response_ups_handler
        )
        result = await self._execute(command, response_handler)
        return result

    async def list_var(self, ups):
        command = ["LIST", "VAR", ups]
        response_handler = NutClient.GenericListCommandHandler(
            command, NutClient.response_var_handler
        )
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
        return result

    async def get_status(self, ups) -> UpsStatus:
        result = await self.get("VAR", ups, "ups.status")
        return UpsStatus(result[0].strip('"'))
