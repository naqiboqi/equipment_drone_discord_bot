import re

from random import randint
from discord import Embed
from discord.ext import commands

class RollTypes(commands.Cog):
    """Roll some dice."""
    
    def __init__(self, bot):
        self.bot = bot
        self.results = []
        self.final_roll = 0
        self.type = ""
        
    async def reset(self):
        """Resets attributes to default values."""
        self.results = []
        self.final_roll = 0
        self.type = ""
        
    async def print_roll(self, ctx: commands.Context):
        """Prints the results of the roll command."""
        
        embed = Embed(title=(F"**{self.type}**"), description=(F"**Rolled** `{self.results}` for `{self.final_roll}`!"))
        embed.set_footer(text=(F"Rolled by {ctx.message.author.display_name}"))
        await ctx.send(embed=embed)
        
        ## Reset attributes.
        await self.reset()
        
    @commands.command(name = 'ability')
    async def ability_roll(self, ctx: commands.Context):
        """Rolls for ability."""
        times = 4
        sides = 6
        self.type = 'Ability Roll' 
        ab_list, temp = [], []
        
        ## Get random number and append lists.
        for roll in range(times):
            ab_roll = randint(1, sides)
            ab_list.append(ab_roll)
            temp.append(ab_roll)

        ## Remove the lowest roll and sum the remaining three.
        ab_list.remove(min(ab_list))
        self.final_roll = sum(ab_list)
        self.results = temp
        
        await self.print_roll(ctx)
        
    @commands.command(name = 'highroll')
    async def advantage_roll(self, ctx: commands.Context):
        """Rolls for advantage. The higher of the two rolls is the result."""
        times = 2
        sides = 20
        self.type = 'Advantage Roll'

        ## Get random number and append lists.
        for roll in range(times):
            new_roll = randint(1, sides)
            self.results.append(new_roll)
        
        ## Gets the higher of the two rolls.
        self.final_roll = max(self.results)
        
        await self.print_roll(ctx)
    
    @commands.command(name = 'lowroll')
    async def disadvantage_roll(self, ctx: commands.Context):
        """Rolls for disadvantage. The lower of the two rolls is the result."""
        times = 2
        sides = 20
        self.type = 'Disadvantage Roll'

        ## Get random number and append lists.
        for rolls in range(times):
            new_roll = randint(1, sides)
            self.results.append(new_roll)
        
        ## Get the lower of the two rolls.
        self.final_roll = min(self.results)
        
        await self.print_roll(ctx)
    
    @commands.command(name = 'roll')
    async def standard_roll(self, ctx: commands.Context):
        """Standard roll. Format message as xdy; where x = sides of the die and y = how many times to roll."""
        roll_choice = ctx.message.content
        
        ## Check for the correct format.
        if re.match("![a-z]+ [\d]+d[\d]+", roll_choice):
            roll_numbers = re.findall(r'\d+', roll_choice)
            times, sides = int(roll_numbers[0]), int(roll_numbers[1])
            self.type = 'Standard Roll'

            ## Get random number and append lists.
            for roll_count in range(times):
                dice_roll = randint(1, sides)
                self.results.append(dice_roll)
                
            ## Get the highest of the rolls in results.
            self.final_roll = max(self.results)
            
            await self.print_roll(ctx)
            
        ## Invalid input.
        else:
            await ctx.send("Invalid format for roll. Try again,.")


## Adds cog to the bot.
def setup(bot: commands.Bot):
    bot.add_cog(RollTypes(bot))