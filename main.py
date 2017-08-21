#!/usr/bin/env python3
import sys
import os

import collections
import datetime
import random
import urllib.parse

import curio
from curio import socket, subprocess

import autoupdater
from ircbot import IrcBot, NO_SPLITTING

SLAP_TEMPLATE = "slaps {slappee} around a bit with {fish}"
FISH = (
    "asyncio", "multiprocessing", "twisted", "django", "pathlib",
    "python 2.7", "a daemon thread",
)

bot = IrcBot()


@bot.on_command(">>>", NO_SPLITTING)
async def annoy_raylu(self, _, recipient, text):
    if recipient == self.nick:
        return
    await self.send_privmsg(recipient, "!py3 " + text)


@bot.on_command("!slap", 1)
async def slap(self, _, recipient, slappee):
    fish = random.choice(FISH)
    await self.send_action(recipient, SLAP_TEMPLATE.format(slappee=slappee,
                                                           fish=fish))


async def termbin(lines):
    async with socket.socket() as sock:
        await sock.connect(('termbin.com', 9999))
        for line in lines:
            assert not line.endswith('\n')
            await sock.send(line.encode('utf-8') + b'\n')

        url = (await sock.recv(1024)).decode('ascii').strip()
        if url == 'Use netcat.':
            return "Sorry, termbin hates me today :("
        return url


# TODO: Move this to the bot's state.
logs = collections.defaultdict(lambda: collections.deque(maxlen=500))


@bot.on_join
async def append_join_to_log(_, sender, channel):
    now = datetime.datetime.now().strftime("%X")
    logs[channel].append(f'[{now}] {sender.nick} joined {channel}')


@bot.on_part
async def append_part_to_log(_, sender, channel, reason=None):
    if reason is None:
        reason = "No reason."

    now = datetime.datetime.now().strftime("%X")
    logs[channel].append(f'[{now}] {sender.nick} parted {channel} ({reason})')

@bot.on_quit
async def append_quit_to_log(_, sender, reason=None):
    if reason is None:
        reason = "No reason."

    now = datetime.datetime.now().strftime("%X")

    # TODO: Only show this in channels where the user was present.
    msg = f'[{now}] {sender.nick} quit ({reason})'

    for log in logs.values():
        log.append(msg)

@bot.on_privmsg
async def append_privmsg_to_log(_, sender, channel, message):
    now = datetime.datetime.now().strftime("%X")
    logs[channel].append(f'[{now}] <{sender.nick}> {message}')


@bot.on_command("!log", 0)
async def send_log(self, sender, channel):
    msg = f"{sender.nick}: Uploading logs, this might take a second..."
    await self.send_privmsg(channel, msg)
    result = await termbin(logs[channel])
    await self.send_privmsg(channel, f"{sender.nick}: {result}")


def _make_url(domain, what2google):
    # example response: 'http://www.lmfgtfy.com/?q=wolo+wolo'
    params = urllib.parse.urlencode({'q': what2google})
    return "http://www.%s/?%s" % (domain, params)


async def _respond(self, recipient, domain, text):
    if recipient == self.nick:
        return

    try:
        target, what2google = text.split(maxsplit=1)
    except ValueError:
        command = "fgoogle" if domain == "lmfgtfy.com" else "google"
        await self.send_privmsg(recipient,
                                "Usage: !%s nick what2google" % command)
        return

    url = _make_url(domain, what2google)

    await self.send_privmsg(recipient, "%s: %s" % (target, url))


@bot.on_command("!google", NO_SPLITTING)
async def google(self, _, recipient, text):
    await _respond(self, recipient, "lmgtfy.com", text)


@bot.on_command("!fgoogle", NO_SPLITTING)
async def fgoogle(self, _, recipient, text):
    await _respond(self, recipient, "lmfgtfy.com", text)


@bot.on_command("!autolog", 1)
async def autolog(self, sender, recipient, argument):
    argument = argument.lower()

    self.state.setdefault("autologgers", [])
    if argument == "on":
        self.state["autologgers"].append(sender.nick)
        await self.send_privmsg(recipient,
                                f"{sender.nick}: You will recieve logs automatically.")
    elif argument == "off":
        if sender.nick in self.state["autologgers"]:
            self.state["autologgers"].remove(sender.nick)
        await self.send_privmsg(recipient,
                                f"{sender.nick}: You will not recieve logs automatically anymore.")
    else:
        await self.send_privmsg(recipient, f"{sender.nick}: USAGE: !autolog on/off")


@bot.on_join
async def autolog_send(self, sender, channel):
    if sender.nick in self.state.get("autologgers", ()):
        result = await termbin(logs[channel])

        # We do a weird trick here.
        # Some clients show NOTICEs of the form "[CHANNELNAME] NOTICE" in the
        # channel buffer named by CHANNELNAME. 
        # We abuse this here to make the logs show up in the channel itself.
        await self.send_notice(sender.nick, f"[{channel}] Logs: {result}")


async def main():
    autoupdater.initialize()

    if len(sys.argv) > 1 and sys.argv[1] == "debug":
        await bot.connect("pyhtonbot2", "chat.freenode.net")
        await bot.join_channel("#8banana")
    else:
        await bot.connect("pyhtonbot", "chat.freenode.net")
        await bot.join_channel("#8banana")
        await bot.join_channel("##learnpython")
        await bot.join_channel("#lpmc")
        await bot.join_channel("#learnprogramming")

    # this only sent to #8banana
    info = (await subprocess.check_output(
        ['git', 'log', '-1', '--pretty=%ai\t%B'])).decode('utf-8')
    update_time, commit_message = info.split("\t", 1)
    commit_summary = commit_message.splitlines()[0]
    await bot.send_privmsg("#8banana",
                           f"Updated at {update_time}: {commit_summary!r}")

    while True:
        try:
            await bot.mainloop()
        except IOError:
            os.execv(__file__, sys.argv)

if __name__ == "__main__":
        curio.run(main)
