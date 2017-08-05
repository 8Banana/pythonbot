#!/usr/bin/env python3
import curio

from ircbot import IrcBot

bot = IrcBot()


@bot.on_privmsg
async def onprivmsg(self, _, recipient, text):
    if recipient == self.nick:
        return
    if text.startswith(">>> "):
        text = text.replace(">>> ", "!py3 ", 1)
        await self.send_privmsg(recipient, text)


async def main():
    await bot.connect("Annoyar", "chat.freenode.net")
    await bot.join_channel("#8banana")
    await bot.mainloop()


if __name__ == "__main__":
    curio.run(main)