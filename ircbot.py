#!/usr/bin/env python3
import collections
import inspect

import curio
from curio import socket


User = collections.namedtuple("User", ["nick", "user", "host"])
Server = collections.namedtuple("Server", ["name"])
Message = collections.namedtuple("Message", ["sender", "command", "args"])

ANY_ARGUMENTS = -1  # any amount of arguments, fully split
NO_SPLITTING = -2  # any amount of arguments, no splitting

ALWAYS_CALLBACK_PRIVMSG = True


def _create_callback_registration(key):
    def _inner(self, func):
        if not inspect.iscoroutinefunction(func):
            raise ValueError("You can only register coroutines!")
        self._message_callbacks[key].append(func)
        return func
    return _inner


class IrcBot:
    def __init__(self, encoding="utf-8"):
        self.nick = None
        self._server = None
        self.encoding = encoding

        self._linebuffer = collections.deque()
        self._sock = socket.socket()

        self._connection_callbacks = []
        self._message_callbacks = {"PRIVMSG": [], "JOIN": [], "PART": []}
        self._command_callbacks = {}

    async def _send(self, *parts):
        data = " ".join(parts).encode(self.encoding) + b"\r\n"
        await self._sock.sendall(data)

    async def _recv_line(self):
        if not self._linebuffer:
            data = bytearray()
            while not data.endswith(b"\r\n"):
                chunk = await self._sock.recv(4096)
                if chunk:
                    data += chunk
                else:
                    raise IOError("Server closed the connection!")

            lines = data.decode(self.encoding, errors='replace').split("\r\n")
            self._linebuffer.extend(lines)
        return self._linebuffer.popleft()

    @staticmethod
    def _split_line(line):
        if line.startswith(":"):
            sender, command, *args = line.split(" ")
            sender = sender[1:]
            if "!" in sender:
                nick, sender = sender.split("!", 1)
                user, host = sender.split("@", 1)
                sender = User(nick, user, host)
            else:
                sender = Server(sender)
        else:
            sender = None
            command, *args = line.split(" ")
        for n, arg in enumerate(args):
            if arg.startswith(":"):
                temp = args[:n]
                temp.append(" ".join(args[n:])[1:])
                args = temp
                break
        return Message(sender, command, args)

    async def connect(self, nick, host, port=6667):
        self.nick = nick
        self._server = (host, port)

        await self._sock.connect(self._server)
        await self._send("NICK", self.nick)
        await self._send("USER", self.nick, "0", "*", ":" + self.nick)
        while True:
            line = await self._recv_line()
            if line.startswith("PING"):
                await self._send(line.replace("PING", "PONG", 1))
                continue
            msg = self._split_line(line)
            if msg.command == "001":
                break

        async with curio.TaskGroup() as g:
            for callback in self._connection_callbacks:
                await g.spawn(callback(self))
            await g.join()

    async def join_channel(self, channel):
        await self._send("JOIN", channel)

    async def send_privmsg(self, recipient, text):
        await self._send("PRIVMSG", recipient, ":" + text)

    async def send_action(self, recipient, action):
        await self._send("PRIVMSG", recipient,
                         ":\x01ACTION {}\x01".format(action))

    async def mainloop(self):
        while True:
            line = await self._recv_line()
            if not line:
                continue
            if line.startswith("PING"):
                await self._send(line.replace("PING", "PONG", 1))
                continue
            msg = self._split_line(line)
            callbacks = self._message_callbacks.get(msg.command, ())
            async with curio.TaskGroup() as g:
                spawn_callbacks = True
                if msg.command == "PRIVMSG":
                    command, *args = msg.args[1].strip().split(" ")
                    cmd_callbacks = self._command_callbacks.get(command, ())
                    for callback, arg_amount in cmd_callbacks:
                        if arg_amount == NO_SPLITTING:
                            spawn_callbacks = False
                            coro = callback(self, msg.sender, msg.args[0],
                                            " ".join(args))
                            await g.spawn(coro)
                        elif arg_amount == ANY_ARGUMENTS or \
                                len(args) == arg_amount:
                            spawn_callbacks = False
                            coro = callback(self, msg.sender, msg.args[0],
                                            *args)
                            await g.spawn(coro)
                if ALWAYS_CALLBACK_PRIVMSG or spawn_callbacks:
                    # Sometimes we don't want to spawn the PRIVMSG callbacks if
                    # this is a command.
                    for callback in callbacks:
                        await g.spawn(callback(self, msg.sender, *msg.args))
                await g.join()

    def on_connect(self, func):
        if not inspect.iscoroutinefunction(func):
            raise ValueError("You can only register coroutines!")
        self._connection_callbacks.append(func)

    on_privmsg = _create_callback_registration("PRIVMSG")
    on_join = _create_callback_registration("JOIN")
    on_part = _create_callback_registration("PART")

    def on_command(self, command, arg_amount=ANY_ARGUMENTS):
        def _inner(func):
            if not inspect.iscoroutinefunction(func):
                raise ValueError("You can only register coroutines!")
            if command not in self._command_callbacks:
                self._command_callbacks[command] = []
            self._command_callbacks[command].append((func, arg_amount))
            return func
        return _inner
