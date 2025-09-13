from discord.ext import commands
import discord
from datetime import datetime, timedelta
import asyncio
import aiohttp

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def add_points(self, user_id, pts, reason="Admin adjustment"):
        # Always write via backend as source of truth using admin-adjust action
        try:
            from bot import BACKEND_API_URL, BOT_SHARED_SECRET
            async with aiohttp.ClientSession() as session:
                payload = {
                    "action": "admin-adjust",
                    "discord_id": user_id,
                    "delta_points": int(pts),
                    "reason": reason,
                }
                
                async with session.post(
                    f"{BACKEND_API_URL}/api/bot/",
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Bot-Secret": BOT_SHARED_SECRET,
                    }
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return True, data.get("total_points", 0)
                    else:
                        error_text = await response.text()
                        return False, error_text
                        
        except Exception as e:
            return False, str(e)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def addpoints(self, ctx, member: commands.MemberConverter, amount: int):
        success, result = await self.add_points(str(member.id), amount, f"Admin added {amount} points")
        
        if success:
            embed = discord.Embed(
                title="✅ Points Added",
                description=f"Added {amount} points to {member.mention}",
                color=0x00ff00
            )
            embed.add_field(name="New Total", value=f"{result} points", inline=True)
        else:
            embed = discord.Embed(
                title="❌ Failed to Add Points",
                description=f"Error adding points to {member.mention}",
                color=0xff0000
            )
            embed.add_field(name="Error", value=str(result), inline=False)
        
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def removepoints(self, ctx, member: commands.MemberConverter, amount: int):
        success, result = await self.add_points(str(member.id), -amount, f"Admin removed {amount} points")
        
        if success:
            embed = discord.Embed(
                title="❌ Points Removed",
                description=f"Removed {amount} points from {member.mention}",
                color=0xff0000
            )
            embed.add_field(name="New Total", value=f"{result} points", inline=True)
        else:
            embed = discord.Embed(
                title="❌ Failed to Remove Points",
                description=f"Error removing points from {member.mention}",
                color=0xff0000
            )
            embed.add_field(name="Error", value=str(result), inline=False)
        
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

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def verifycourse(self, ctx, member: commands.MemberConverter, course_name: str, points: int, *, notes: str = ""):
        """Admin command to confirm certification/course completion"""
        try:
            user_id = str(member.id)
            
            # Award points for course completion
            success, result = await self.add_points(user_id, points, f"Course completion: {course_name}")
            
            if not success:
                await ctx.send(f"❌ Error awarding points: {result}")
                return
            
            embed = discord.Embed(
                title="🎓 Course Completion Verified",
                description=f"Course completion has been verified and points awarded!",
                color=0x00ff00
            )
            
            embed.add_field(
                name="👤 Student",
                value=member.mention,
                inline=True
            )
            
            embed.add_field(
                name="📚 Course",
                value=course_name,
                inline=True
            )
            
            embed.add_field(
                name="🎯 Points Awarded",
                value=f"**{points}** points",
                inline=True
            )
            
            embed.add_field(
                name="📊 New Total",
                value=f"**{result}** points",
                inline=True
            )
            
            embed.add_field(
                name="👨‍⚖️ Verified By",
                value=ctx.author.display_name,
                inline=True
            )
            
            if notes:
                embed.add_field(
                    name="📝 Notes",
                    value=notes,
                    inline=False
                )
            
            embed.add_field(
                name="🏆 Achievement",
                value="Congratulations on completing your course!",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
            # Notify the student
            try:
                student_embed = discord.Embed(
                    title="🎉 Course Completion Verified!",
                    description="Congratulations! Your course completion has been verified!",
                    color=0x00ff00
                )
                
                student_embed.add_field(
                    name="📚 Course",
                    value=course_name,
                    inline=True
                )
                
                student_embed.add_field(
                    name="🎯 Points Earned",
                    value=f"**{points}** points",
                    inline=True
                )
                
                if notes:
                    student_embed.add_field(
                        name="📝 Notes",
                        value=notes,
                        inline=False
                    )
                
                await member.send(embed=student_embed)
                
            except discord.Forbidden:
                await ctx.send(f"⚠️ Could not send DM to {member.mention} - please notify them manually")
            
        except Exception as e:
            await ctx.send(f"❌ Error verifying course completion: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def highlight(self, ctx, period: str = "week"):
        """Admin command to highlight top contributors for the week/month"""
        try:
            # Validate period
            valid_periods = ["week", "month", "all"]
            if period.lower() not in valid_periods:
                await ctx.send(f"❌ Invalid period. Available periods: {', '.join(valid_periods)}")
                return
            
            period = period.lower()
            
            # Fetch top contributors from backend
            try:
                from bot import BACKEND_API_URL, BOT_SHARED_SECRET
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{BACKEND_API_URL}/api/bot/",
                        json={"action": "top-contributors", "period": period, "limit": 5},
                        headers={"Content-Type": "application/json", "X-Bot-Secret": BOT_SHARED_SECRET},
                    ) as resp:
                        if resp.status != 200:
                            await ctx.send("❌ Failed to fetch top contributors.")
                            return
                        data = await resp.json()
            except Exception:
                await ctx.send("❌ Error connecting to backend.")
                return
            
            contributors = data.get('contributors', [])
            period_name = data.get('period_name', period.title())
            total_activities = data.get('total_activities', 0)
            
            embed = discord.Embed(
                title=f"🌟 Top Contributors - {period_name}",
                description=f"Recognizing our most active community members this {period_name.lower()}",
                color=0xffd700
            )
            
            if not contributors:
                embed.add_field(
                    name="📊 No Data",
                    value=f"No activity data available for this {period_name.lower()}.",
                    inline=False
                )
            else:
                for i, contributor in enumerate(contributors, 1):
                    user_id = contributor.get('discord_id')
                    points = contributor.get('points', 0)
                    activities = contributor.get('activities', 0)
                    username = contributor.get('username', f'User {user_id}')
                    
                    # Get Discord user if possible
                    try:
                        user = await self.bot.fetch_user(int(user_id))
                        display_name = user.display_name
                    except:
                        display_name = username
                    
                    # Trophy emojis for top 3
                    trophy = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**#{i}**"
                    
                    contributor_info = f"**{points:,}** points earned\n"
                    contributor_info += f"**{activities}** activities completed"
                    
                    embed.add_field(
                        name=f"{trophy} {display_name}",
                        value=contributor_info,
                        inline=True
                    )
            
            embed.add_field(
                name="📈 Total Activities",
                value=f"**{total_activities}** activities this {period_name.lower()}",
                inline=True
            )
            
            embed.add_field(
                name="🎯 Recognition",
                value="Thank you for your dedication to the community!",
                inline=False
            )
            
            embed.set_footer(text=f"Data from {period_name} • Use !highlight week/month/all")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error highlighting contributors: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def audit(self, ctx, hours: int = 24, user: commands.MemberConverter = None):
        """Admin command to view logs of all point-related activities"""
        try:
            # Fetch audit logs from backend
            try:
                from bot import BACKEND_API_URL, BOT_SHARED_SECRET
                async with aiohttp.ClientSession() as session:
                    payload = {
                        "action": "audit-logs",
                        "hours": hours,
                        "limit": 50
                    }
                    
                    if user:
                        payload["discord_id"] = str(user.id)
                    
                    async with session.post(
                        f"{BACKEND_API_URL}/api/bot/",
                        json=payload,
                        headers={"Content-Type": "application/json", "X-Bot-Secret": BOT_SHARED_SECRET},
                    ) as resp:
                        if resp.status != 200:
                            await ctx.send("❌ Failed to fetch audit logs.")
                            return
                        data = await resp.json()
            except Exception:
                await ctx.send("❌ Error connecting to backend.")
                return
            
            logs = data.get('logs', [])
            total_logs = data.get('total_logs', 0)
            summary = data.get('summary', {})
            
            embed = discord.Embed(
                title="📋 Point Activity Audit",
                description=f"Audit logs for the last {hours} hours",
                color=0x0099ff
            )
            
            if user:
                embed.add_field(
                    name="👤 Filtered User",
                    value=user.mention,
                    inline=True
                )
            
            # Summary statistics
            if summary:
                embed.add_field(
                    name="📊 Summary",
                    value=f"**{summary.get('total_activities', 0)}** activities\n"
                          f"**{summary.get('total_points', 0):,}** points awarded\n"
                          f"**{summary.get('unique_users', 0)}** users active",
                    inline=True
                )
            
            if not logs:
                embed.add_field(
                    name="📝 No Activity",
                    value=f"No point-related activity found in the last {hours} hours.",
                    inline=False
                )
            else:
                # Show recent activities (limit to fit Discord embed)
                recent_logs = logs[:10]  # Show first 10 logs
                
                for log in recent_logs:
                    user_id = log.get('discord_id')
                    action = log.get('action', 'Unknown')
                    points = log.get('points', 0)
                    timestamp = log.get('timestamp', '')
                    details = log.get('details', '')
                    
                    # Get Discord user if possible
                    try:
                        user_obj = await self.bot.fetch_user(int(user_id))
                        username = user_obj.display_name
                    except:
                        username = log.get('username', f'User {user_id}')
                    
                    # Format timestamp
                    time_str = timestamp[:19] if timestamp else 'Unknown time'
                    
                    log_info = f"**{action}**"
                    if points != 0:
                        log_info += f" ({points:+d} pts)"
                    if details:
                        log_info += f"\n*{details[:100]}{'...' if len(details) > 100 else ''}*"
                    
                    embed.add_field(
                        name=f"{time_str} - {username}",
                        value=log_info,
                        inline=False
                    )
                
                if len(logs) > 10:
                    embed.add_field(
                        name="📝 Note",
                        value=f"Showing 10 of {len(logs)} recent activities. Total: {total_logs} activities.",
                        inline=False
                    )
            
            embed.add_field(
                name="🔍 Audit Info",
                value=f"Period: Last {hours} hours\n"
                      f"Total logs: {total_logs}\n"
                      f"Generated by: {ctx.author.display_name}",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error fetching audit logs: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def approveevent(self, ctx, member: commands.MemberConverter, *, notes: str = ""):
        """Approve an event attendance submission and award points"""
        try:
            success, result = await self.add_points(str(member.id), 15, f"Event attendance approved: {notes}")
            
            if success:
                embed = discord.Embed(
                    title="✅ Event Attendance Approved!",
                    description=f"Event attendance has been approved and points awarded!",
                    color=0x00ff00
                )
                
                embed.add_field(
                    name="👤 User",
                    value=member.mention,
                    inline=True
                )
                
                embed.add_field(
                    name="🎯 Points Awarded",
                    value=f"**15 points**",
                    inline=True
                )
                
                embed.add_field(
                    name="📊 New Total",
                    value=f"**{result} points**",
                    inline=True
                )
                
                embed.add_field(
                    name="👨‍⚖️ Reviewed By",
                    value=ctx.author.display_name,
                    inline=True
                )
                
                if notes:
                    embed.add_field(
                        name="📝 Notes",
                        value=notes,
                        inline=False
                    )
                
                await ctx.send(embed=embed)
                
                # Notify the user
                try:
                    user_embed = discord.Embed(
                        title="🎉 Your Event Attendance Was Approved!",
                        description=f"Great news! Your event attendance has been approved by an admin.",
                        color=0x00ff00
                    )
                    user_embed.add_field(name="🎯 Points Earned", value=f"**15** points", inline=True)
                    user_embed.add_field(name="📊 Your New Total", value=f"**{result}** points", inline=True)
                    if notes:
                        user_embed.add_field(name="📝 Admin Notes", value=notes, inline=False)
                    await member.send(embed=user_embed)
                except discord.Forbidden:
                    print(f"Could not send DM to user {member.id} for event approval.")
            else:
                await ctx.send(f"❌ Failed to approve event attendance: {result}")
                
        except Exception as e:
            await ctx.send(f"❌ Error approving event attendance: {e}")
            print(f"Error in approveevent command: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def rejectevent(self, ctx, member: commands.MemberConverter, *, reason: str = "No reason provided"):
        """Reject an event attendance submission"""
        try:
            embed = discord.Embed(
                title="❌ Event Attendance Rejected",
                description=f"Event attendance submission has been rejected.",
                color=0xff0000
            )
            
            embed.add_field(
                name="👤 User",
                value=member.mention,
                inline=True
            )
            
            embed.add_field(
                name="👨‍⚖️ Reviewed By",
                value=ctx.author.display_name,
                inline=True
            )
            
            embed.add_field(
                name="📝 Reason",
                value=reason,
                inline=False
            )
            
            await ctx.send(embed=embed)
            
            # Notify the user
            try:
                user_embed = discord.Embed(
                    title="🚫 Your Event Attendance Was Rejected",
                    description=f"Unfortunately, your event attendance submission was not approved.",
                    color=0xff0000
                )
                user_embed.add_field(name="📝 Reason", value=reason, inline=False)
                user_embed.add_field(name="👨‍⚖️ Reviewed By", value=ctx.author.display_name, inline=True)
                await member.send(embed=user_embed)
            except discord.Forbidden:
                print(f"Could not send DM to user {member.id} for event rejection.")
                
        except Exception as e:
            await ctx.send(f"❌ Error rejecting event attendance: {e}")
            print(f"Error in rejectevent command: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def approvelinkedin(self, ctx, member: commands.MemberConverter, *, notes: str = ""):
        """Approve a LinkedIn update submission and award points"""
        try:
            success, result = await self.add_points(str(member.id), 5, f"LinkedIn update approved: {notes}")
            
            if success:
                embed = discord.Embed(
                    title="✅ LinkedIn Update Approved!",
                    description=f"LinkedIn update has been approved and points awarded!",
                    color=0x00ff00
                )
                
                embed.add_field(
                    name="👤 User",
                    value=member.mention,
                    inline=True
                )
                
                embed.add_field(
                    name="🎯 Points Awarded",
                    value=f"**5 points**",
                    inline=True
                )
                
                embed.add_field(
                    name="📊 New Total",
                    value=f"**{result} points**",
                    inline=True
                )
                
                embed.add_field(
                    name="👨‍⚖️ Reviewed By",
                    value=ctx.author.display_name,
                    inline=True
                )
                
                if notes:
                    embed.add_field(
                        name="📝 Notes",
                        value=notes,
                        inline=False
                    )
                
                await ctx.send(embed=embed)
                
                # Notify the user
                try:
                    user_embed = discord.Embed(
                        title="🎉 Your LinkedIn Update Was Approved!",
                        description=f"Great news! Your LinkedIn update has been approved by an admin.",
                        color=0x00ff00
                    )
                    user_embed.add_field(name="🎯 Points Earned", value=f"**5** points", inline=True)
                    user_embed.add_field(name="📊 Your New Total", value=f"**{result}** points", inline=True)
                    if notes:
                        user_embed.add_field(name="📝 Admin Notes", value=notes, inline=False)
                    await member.send(embed=user_embed)
                except discord.Forbidden:
                    print(f"Could not send DM to user {member.id} for LinkedIn approval.")
            else:
                await ctx.send(f"❌ Failed to approve LinkedIn update: {result}")
                
        except Exception as e:
            await ctx.send(f"❌ Error approving LinkedIn update: {e}")
            print(f"Error in approvelinkedin command: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def rejectlinkedin(self, ctx, member: commands.MemberConverter, *, reason: str = "No reason provided"):
        """Reject a LinkedIn update submission"""
        try:
            embed = discord.Embed(
                title="❌ LinkedIn Update Rejected",
                description=f"LinkedIn update submission has been rejected.",
                color=0xff0000
            )
            
            embed.add_field(
                name="👤 User",
                value=member.mention,
                inline=True
            )
            
            embed.add_field(
                name="👨‍⚖️ Reviewed By",
                value=ctx.author.display_name,
                inline=True
            )
            
            embed.add_field(
                name="📝 Reason",
                value=reason,
                inline=False
            )
            
            await ctx.send(embed=embed)
            
            # Notify the user
            try:
                user_embed = discord.Embed(
                    title="🚫 Your LinkedIn Update Was Rejected",
                    description=f"Unfortunately, your LinkedIn update submission was not approved.",
                    color=0xff0000
                )
                user_embed.add_field(name="📝 Reason", value=reason, inline=False)
                user_embed.add_field(name="👨‍⚖️ Reviewed By", value=ctx.author.display_name, inline=True)
                await member.send(embed=user_embed)
            except discord.Forbidden:
                print(f"Could not send DM to user {member.id} for LinkedIn rejection.")
                
        except Exception as e:
            await ctx.send(f"❌ Error rejecting LinkedIn update: {e}")
            print(f"Error in rejectlinkedin command: {e}")

async def setup(bot):
    await bot.add_cog(Admin(bot))
