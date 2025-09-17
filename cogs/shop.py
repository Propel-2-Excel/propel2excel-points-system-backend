import discord
from discord.ext import commands
import aiohttp

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def shop(self, ctx):
        embed = discord.Embed(
            title="🚧 Feature in Development",
            description="The shop feature is currently being developed and will be available soon!",
            color=0xffaa00
        )
        embed.add_field(
            name="What's Coming",
            value="• Browse available rewards and incentives\n• View point requirements for each item\n• Check stock availability\n• See detailed reward descriptions",
            inline=False
        )
        embed.add_field(
            name="Stay Tuned",
            value="We're working hard to bring you an amazing shop experience!",
            inline=False
        )
        await ctx.send(embed=embed)


    @commands.command()
    async def redeem(self, ctx, reward_id: int = None):
        embed = discord.Embed(
            title="🚧 Feature in Development",
            description="The redeem feature is currently being developed and will be available soon!",
            color=0xffaa00
        )
        embed.add_field(
            name="What's Coming",
            value="• Redeem rewards with your earned points\n• Automatic point deduction\n• Confirmation and tracking system\n• Direct contact from our team",
            inline=False
        )
        embed.add_field(
            name="Stay Tuned",
            value="We're working hard to bring you an amazing redemption experience!",
            inline=False
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Shop(bot))
