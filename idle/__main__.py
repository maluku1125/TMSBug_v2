import argparse
import asyncio
import configparser
import sys

import discord
from TMSdiscordbot_Rebuild import TMSBot

try:
    _TMSBot_CONF = configparser.ConfigParser()
    _TMSBot_CONF.read("config.ini", encoding="utf-8")
except FileNotFoundError:
    print("`config.ini` file missing.")
    sys.exit(1)

discord.voice_client.VoiceClient.warn_nacl = False


def resolve_intents() -> discord.Intents:
    "Resolves configured intents to discord format"
    intents = discord.Intents.default()
    intents.members = _TMSBot_CONF.getboolean("intents", "members", fallback=False)
    intents.presences = _TMSBot_CONF.getboolean("intents", "presences", fallback=False)
    intents.message_content = _TMSBot_CONF.getboolean(
        "intents", "message_content", fallback=False
    )
    return intents

def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    tmsbot = TMSBot(config=_TMSBot_CONF, intents=resolve_intents())
    loop.run_until_complete(
        tmsbot.start(_TMSBot_CONF["discord"]["token"], reconnect=True)
    )

if __name__ == "__main__":
    main()
