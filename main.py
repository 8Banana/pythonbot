#!/usr/bin/env python3
import urllib.parse

import curio

from ircbot import IrcBot

bot = IrcBot()


@bot.on_privmsg
async def annoy_raylu(self, _, recipient, text):
    if recipient == self.nick:
        return
    if text.startswith(">>> "):
        text = text.replace(">>>", "!py3", 1)
        await self.send_privmsg(recipient, text)


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
