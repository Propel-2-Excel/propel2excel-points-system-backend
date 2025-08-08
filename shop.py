from discord.ext import commands
import aiohttp

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def shop(self, ctx):
        try:
            from bot import BACKEND_API_URL
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{BACKEND_API_URL}/api/incentives/") as resp:
                    if resp.status != 200:
                        await ctx.send("❌ Failed to fetch shop items.")
                        return
                    data = await resp.json()
                    if not data:
                        await ctx.send("The shop is currently empty!")
                        return
                    msg = "**Available Incentives:**\n"
                    for item in data:
                        msg += f"{item.get('id')}. {item.get('name')} — {item.get('points_required')} points\n"
                    msg += "\nUse `!redeem <id>` to redeem an incentive."
                    await ctx.send(msg)
        except Exception:
            await ctx.send("❌ Error fetching shop items.")

    @commands.command()
    async def redeem(self, ctx, reward_id: int):
        try:
            from bot import BACKEND_API_URL, BOT_SHARED_SECRET
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BACKEND_API_URL}/api/bot/",
                    json={"action": "redeem", "discord_id": str(ctx.author.id), "incentive_id": reward_id},
                    headers={"Content-Type": "application/json", "X-Bot-Secret": BOT_SHARED_SECRET},
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        await ctx.send(f"❌ Failed to redeem: {text[:200]}")
                        return
                    data = await resp.json()
                    await ctx.send(f"{ctx.author.mention}, you have successfully redeemed **{data.get('message','item')}**! Our team will contact you shortly.")
        except Exception:
            await ctx.send("❌ Error redeeming incentive.")

async def setup(bot):
    await bot.add_cog(Shop(bot))
