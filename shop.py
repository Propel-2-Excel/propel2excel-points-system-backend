import discord
from discord.ext import commands
import aiohttp

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def shop(self, ctx):
        try:
            from bot import BACKEND_API_URL, BOT_SHARED_SECRET
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BACKEND_API_URL}/api/bot/",
                    json={"action": "get-shop-items"},
                    headers={"Content-Type": "application/json", "X-Bot-Secret": BOT_SHARED_SECRET},
                ) as resp:
                    if resp.status != 200:
                        await ctx.send("❌ Failed to fetch shop items.")
                        return
                    data = await resp.json()
                    if not data.get('success') or not data.get('items'):
                        await ctx.send("The shop is currently empty!")
                        return
                    
                    items = data.get('items', [])
                    msg = "**🛍️ Available Incentives:**\n\n"
                    for item in items:
                        stock_info = f" (Stock: {item.get('stock_available', 'N/A')})" if item.get('stock_available', 0) > 0 else " (Out of Stock)"
                        msg += f"**{item.get('id')}.** {item.get('name')} — **{item.get('points_required')} points**{stock_info}\n"
                    
                    msg += "\n**📋 How to Redeem:**\n"
                    msg += "1️⃣ Use `!points` to check your current points\n"
                    msg += "2️⃣ Use `!redeem <id>` where `<id>` is the **number** next to the item\n"
                    msg += "3️⃣ **Examples:**\n"
                    if items:
                        msg += f"   • `!redeem {items[0].get('id')}` → Redeem {items[0].get('name')}\n"
                        if len(items) > 1:
                            msg += f"   • `!redeem {items[1].get('id')}` → Redeem {items[1].get('name')}\n"
                        if len(items) > 2:
                            msg += f"   • `!redeem {items[2].get('id')}` → Redeem {items[2].get('name')}\n"
                    msg += "\n**💡 Important:**\n"
                    msg += "• `<id>` = The **number** (1, 2, 3, etc.) shown next to each item\n"
                    msg += "• Make sure you have enough points before redeeming!\n"
                    msg += "• Our team will contact you after successful redemption"
                    await ctx.send(msg)
        except Exception as e:
            await ctx.send(f"❌ Error fetching shop items: {e}")


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
