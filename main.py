#!/usr/bin/env python3
import random
import urllib.parse

import curio

from ircbot import IrcBot

SLAP_TEMPLATE = "slaps {slapee} around a bit with {fish}"
FISH = (
    "asyncio", "multiprocessing", "twisted", "django", "pathlib",
    "python 2.7", "a daemon thread",
)

bot = IrcBot()


@bot.on_privmsg
async def annoy_raylu(self, _, recipient, text):
    if recipient == self.nick:
        return
    if text.startswith(">>> "):
        text = text.replace(">>>", "!py3", 1)
        await self.send_privmsg(recipient, text)


@bot.on_command("!slap", 1)
async def slap(self, sender, recipient, slapee):
    fish = random.choice(FISH)
    await self.send_action(recipient, SLAP_TEMPLATE.format(slapee=slapee,
                                                           fish=fish))


@bot.on_privmsg
async def google(self, _, recipient, text):
    if recipient == self.nick:
        return

    if text.startswith(("!google ", "!fgoogle ")):
        try:
            command, target, what2google = text.split(maxsplit=2)
        except ValueError:
            command = text.split(maxsplit=1)[0]
            await self.send_privmsg(
                recipient, "Usage: %s nick what2google" % command)
            return

        if 'f' in command:
            domain = 'lmfgtfy.com'
        else:
            domain = 'lmgtfy.com'

        # example response: 'http://www.lmfgtfy.com/?q=wolo+wolo'
        params = urllib.parse.urlencode({'q': what2google})
        response = 'http://www.%s/?%s' % (domain, params)

        await self.send_privmsg(recipient, "%s: %s" % (target, response))


async def main():
    await bot.connect("macigpythonbot", "chat.freenode.net")
    await bot.join_channel("#8banana")
    await bot.join_channel("##learnpython")
    await bot.mainloop()


if __name__ == "__main__":
    curio.run(main)
