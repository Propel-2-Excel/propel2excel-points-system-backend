from discord.ext import commands
import discord
from datetime import datetime, timedelta
import asyncio
import aiohttp

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def add_points(self, user_id, pts):
        # Always write via backend as source of truth
        try:
            from bot import update_user_points_in_backend
            asyncio.create_task(update_user_points_in_backend(user_id, int(pts), "Admin adjustment"))
        except Exception:
            pass

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def addpoints(self, ctx, member: commands.MemberConverter, amount: int):
        self.add_points(str(member.id), amount)
        embed = discord.Embed(
            title="✅ Points Added",
            description=f"Added {amount} points to {member.mention}",
            color=0x00ff00
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def removepoints(self, ctx, member: commands.MemberConverter, amount: int):
        self.add_points(str(member.id), -amount)
        embed = discord.Embed(
            title="❌ Points Removed",
            description=f"Removed {amount} points from {member.mention}",
            color=0xff0000
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def resetpoints(self, ctx, member: commands.MemberConverter):
        # Implement by admin-adjust negative of current total via backend summary
        try:
            from bot import BACKEND_API_URL, BOT_SHARED_SECRET
            async with aiohttp.ClientSession() as session:
                # Fetch current total via summary
                async with session.post(
                    f"{BACKEND_API_URL}/api/bot/",
                    json={"action": "summary", "discord_id": str(member.id), "limit": 1},
                    headers={"Content-Type": "application/json", "X-Bot-Secret": BOT_SHARED_SECRET},
                ) as resp:
                    if resp.status != 200:
                        await ctx.send("❌ Failed to fetch user points for reset.")
                        return
                    data = await resp.json()
                    total = int(data.get("total_points", 0))
                # Apply negative delta
                async with session.post(
                    f"{BACKEND_API_URL}/api/bot/",
                    json={"action": "admin-adjust", "discord_id": str(member.id), "delta_points": -total, "reason": "Reset by admin"},
                    headers={"Content-Type": "application/json", "X-Bot-Secret": BOT_SHARED_SECRET},
                ) as resp2:
                    if resp2.status != 200:
                        await ctx.send("❌ Failed to reset points.")
                        return
        except Exception:
            await ctx.send("❌ Error resetting points.")
            return
        embed = discord.Embed(
            title="🔄 Points Reset",
            description=f"Reset points for {member.mention}",
            color=0xffaa00
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def stats(self, ctx):
        """Show bot statistics and activity"""
        # Simplified: fetch leaderboard page 1 and activitylog to surface key stats
        total_users = 0
        total_points = 0
        today_activity = 0
        try:
            from bot import BACKEND_API_URL, BOT_SHARED_SECRET
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BACKEND_API_URL}/api/bot/",
                    json={"action": "leaderboard", "page": 1, "page_size": 1},
                    headers={"Content-Type": "application/json", "X-Bot-Secret": BOT_SHARED_SECRET},
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        total_users = data.get("total_users", 0)
                        if data.get("results"):
                            total_points = data["results"][0].get("total_points", 0)  # best-effort
                async with session.post(
                    f"{BACKEND_API_URL}/api/bot/",
                    json={"action": "activitylog", "hours": 24, "limit": 1000},
                    headers={"Content-Type": "application/json", "X-Bot-Secret": BOT_SHARED_SECRET},
                ) as resp2:
                    if resp2.status == 200:
                        data2 = await resp2.json()
                        today_activity = len(data2.get("items", []))
        except Exception:
            pass
        
        embed = discord.Embed(
            title="📊 Bot Statistics",
            description="Current bot activity and metrics",
            color=0x0099ff
        )
        embed.add_field(name="Total Users", value=f"{total_users}", inline=True)
        embed.add_field(name="Total Points Distributed", value=f"{total_points:,}", inline=True)
        embed.add_field(name="Today's Activities", value=f"{today_activity}", inline=True)
        embed.add_field(name="Backend", value="Supabase", inline=True)
        embed.add_field(name="Bot Uptime", value=f"<t:{int(self.bot.start_time.timestamp())}:R>", inline=True)
        
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def topusers(self, ctx, limit: int = 10):
        """Show top users by points"""
        embed = discord.Embed(
            title="🏆 Top Users by Points",
            description=f"Top {limit} users with the most points",
            color=0xffd700
        )
        try:
            from bot import BACKEND_API_URL, BOT_SHARED_SECRET
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BACKEND_API_URL}/api/bot/",
                    json={"action": "leaderboard", "page": 1, "page_size": limit},
                    headers={"Content-Type": "application/json", "X-Bot-Secret": BOT_SHARED_SECRET},
                ) as resp:
                    if resp.status != 200:
                        await ctx.send("❌ Failed to fetch top users.")
                        return
                    data = await resp.json()
                    for item in data.get("results", []):
                        user_id = item.get("discord_id")
                        points = item.get("total_points", 0)
                        try:
                            user = await self.bot.fetch_user(int(user_id))
                            username = user.display_name
                        except Exception:
                            username = item.get("username") or f"User {user_id}"
                        embed.add_field(
                            name=f"#{item.get('position')} {username}",
                            value=f"{points:,} points",
                            inline=True
                        )
        except Exception:
            await ctx.send("❌ Error fetching top users.")
            return
        
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def clearwarnings(self, ctx, member: commands.MemberConverter):
        """Clear warnings for a user"""
        try:
            from bot import BACKEND_API_URL, BOT_SHARED_SECRET
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BACKEND_API_URL}/api/bot/",
                    json={"action": "clear-warnings", "discord_id": str(member.id)},
                    headers={"Content-Type": "application/json", "X-Bot-Secret": BOT_SHARED_SECRET},
                ) as resp:
                    if resp.status != 200:
                        await ctx.send("❌ Failed to clear warnings.")
                        return
        except Exception:
            await ctx.send("❌ Error clearing warnings.")
            return
        
        embed = discord.Embed(
            title="✅ Warnings Cleared",
            description=f"Cleared all warnings for {member.mention}",
            color=0x00ff00
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def suspenduser(self, ctx, member: commands.MemberConverter, duration_minutes: int):
        """Suspend a user's ability to earn points"""
        try:
            from bot import BACKEND_API_URL, BOT_SHARED_SECRET
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BACKEND_API_URL}/api/bot/",
                    json={"action": "suspend-user", "discord_id": str(member.id), "duration_minutes": duration_minutes},
                    headers={"Content-Type": "application/json", "X-Bot-Secret": BOT_SHARED_SECRET},
                ) as resp:
                    if resp.status != 200:
                        await ctx.send("❌ Failed to suspend user.")
                        return
        except Exception:
            await ctx.send("❌ Error suspending user.")
            return
        
        embed = discord.Embed(
            title="⏸️ User Suspended",
            description=f"{member.mention} is suspended from earning points for {duration_minutes} minutes",
            color=0xffaa00
        )
        embed.add_field(name="Suspension Ends", value=f"<t:{int(suspension_end.timestamp())}:R>", inline=True)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def unsuspenduser(self, ctx, member: commands.MemberConverter):
        """Remove suspension from a user"""
        try:
            from bot import BACKEND_API_URL, BOT_SHARED_SECRET
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BACKEND_API_URL}/api/bot/",
                    json={"action": "unsuspend-user", "discord_id": str(member.id)},
                    headers={"Content-Type": "application/json", "X-Bot-Secret": BOT_SHARED_SECRET},
                ) as resp:
                    if resp.status != 200:
                        await ctx.send("❌ Failed to unsuspend user.")
                        return
        except Exception:
            await ctx.send("❌ Error unsuspending user.")
            return
        
        embed = discord.Embed(
            title="✅ User Unsuspended",
            description=f"{member.mention} can now earn points again",
            color=0x00ff00
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def activitylog(self, ctx, hours: int = 24):
        """Show recent activity log"""
        try:
            from bot import BACKEND_API_URL, BOT_SHARED_SECRET
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BACKEND_API_URL}/api/bot/",
                    json={"action": "activitylog", "hours": hours, "limit": 20},
                    headers={"Content-Type": "application/json", "X-Bot-Secret": BOT_SHARED_SECRET},
                ) as resp:
                    if resp.status != 200:
                        await ctx.send("❌ Failed to fetch activity log.")
                        return
                    data = await resp.json()
                    items = data.get("items", [])
                    if not items:
                        await ctx.send(f"No activity in the last {hours} hours.")
                        return
        except Exception:
            await ctx.send("❌ Error fetching activity log.")
            return
        
        embed = discord.Embed(
            title=f"📝 Activity Log (Last {hours}h)",
            description="Recent point-earning activities",
            color=0x0099ff
        )
        for item in items:
            user_id = item.get("discord_id")
            try:
                user = await self.bot.fetch_user(int(user_id))
                username = user.display_name
            except Exception:
                username = item.get("username") or f"User {user_id}"
            embed.add_field(
                name=f"{item.get('timestamp', '')[:19]} - {username}",
                value=f"{item.get('action')} (+{item.get('points', 0)} pts)",
                inline=False
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Admin(bot))
