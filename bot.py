import discord
import os
import traceback

from asyncio import sleep
from discord.ext import commands
from dotenv import load_dotenv

from constants import status

###---------------------------------------------------------------------###
bot = commands.Bot(command_prefix="!")

@bot.event
async def on_ready():
    print(F"{bot.user.name} is now online. Beep boop!")
    # Change the bot"s status every two hours.
    while True:
        game_status = await status.chooseGame()
        await bot.change_presence(activity = discord.Game(name=game_status))
        await sleep(7200)   
        
## Try to load the bot's extensions.
print("Loading...\n")
for filename in os.listdir("./cogs"):
    try:
        if filename.endswith(".py"):
            bot.load_extension(F"cogs.{filename[:-3]}")
            
    except Exception:
        print(F"\nFailed to load {filename}.\n")
        print(traceback.format_exc())
    else:
        print(F"{filename} sucessfully loaded...")

## Get the bot's token.
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)