import discord
from discord.ext import commands

PINS_CHANNEL = 1006788425350922311

class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command(name="pin")
    async def pin_msg(self, ctx):
        message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        channel = self.bot.get_channel(PINS_CHANNEL)

        await channel.send(F"I have sent: {message}")
    
    @commands.command(name="ping")
    async def ping_bot(self, ctx):
        """Sends the bot's latency."""
        await ctx.reply(F"pewpew! {round(self.bot.latency * 1000)} ms")
        
    @commands.command(name="avatar")
    async def get_avatar(self, ctx):
        author = ctx.message.author
        filename = F"{author}_avatar.jpg"
        
        await ctx.author.avatar_url.save(filename)
        file = discord.File(fp=filename)
        
        await ctx.send("Here is your pfp =>", file=file)
        
def setup(bot):
    bot.add_cog(Utilities(bot))