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

    async def clear_user_caches(self, user_id):
        """Clear all caches that could be affected by user point changes"""
        try:
            from bot import BACKEND_API_URL, BOT_SHARED_SECRET
            async with aiohttp.ClientSession() as session:
                # Clear all user-specific caches
                async with session.post(
                    f"{BACKEND_API_URL}/api/cache/clear_user/",
                    json={"user_id": user_id},
                    headers={"Authorization": f"Bearer {BOT_SHARED_SECRET}"},
                ) as resp:
                    pass  # Don't fail if cache clear fails
        except Exception:
            pass  # Don't fail the main command if cache clearing fails

    def find_reward_matches(self, rewards, search_term):
        """Smart reward matching with conflict detection"""
        search_lower = search_term.lower()
        
        # First try exact matches
        exact_matches = [r for r in rewards if r.get('name', '').lower() == search_lower]
        if exact_matches:
            return exact_matches, "exact"
        
        # Then try partial matches
        partial_matches = [r for r in rewards if search_lower in r.get('name', '').lower()]
        if partial_matches:
            return partial_matches, "partial"
        
        return [], "none"

    def get_unique_words(self, matches):
        """Get unique words that could help differentiate between matches"""
        all_words = []
        for match in matches:
            words = match.get('name', '').lower().split()
            all_words.extend(words)
        
        # Find words that appear in only one match
        unique_words = []
        for word in set(all_words):
            count = sum(1 for match in matches if word in match.get('name', '').lower())
            if count == 1:
                unique_words.append(word)
        
        return ", ".join(unique_words[:3]) if unique_words else "template, review, coaching"

    async def handle_reward_command(self, ctx, reward_name, action, action_past_tense):
        """Handle reward enable/disable commands with stock management"""
        try:
            from bot import BACKEND_API_URL, BOT_SHARED_SECRET
            async with aiohttp.ClientSession() as session:
                # First find the reward by name
                async with session.get(
                    f"{BACKEND_API_URL}/api/incentives/admin_list/",
                    headers={"Authorization": f"Bearer {BOT_SHARED_SECRET}"},
                ) as resp:
                    if resp.status != 200:
                        await ctx.send("❌ Failed to fetch rewards.")
                        return
                    rewards = await resp.json()
                
                # Smart matching
                matches, match_type = self.find_reward_matches(rewards, reward_name)
                
                if not matches:
                    # No matches found - show suggestions
                    embed = discord.Embed(
                        title="❌ Reward Not Found",
                        description=f"No rewards found matching: `{reward_name}`",
                        color=0xff0000
                    )
                    
                    # Show similar rewards
                    similar = []
                    for r in rewards:
                        name_lower = r.get('name', '').lower()
                        if any(word in name_lower for word in reward_name.lower().split()):
                            similar.append(r)
                    
                    if similar:
                        embed.add_field(
                            name="💡 Did you mean?",
                            value="\n".join([f"• {r.get('name')}" for r in similar[:5]]),
                            inline=False
                        )
                    
                    embed.add_field(
                        name="💡 Tip",
                        value="Use `!rewards` to see all available rewards",
                        inline=False
                    )
                    await ctx.send(embed=embed)
                    return
                
                if len(matches) > 1:
                    # Multiple matches found - show them to admin
                    embed = discord.Embed(
                        title="🔍 Multiple Rewards Found",
                        description=f"Found {len(matches)} rewards matching `{reward_name}`:",
                        color=0xffaa00
                    )
                    
                    for i, match in enumerate(matches, 1):
                        stock_status = "In Stock" if match.get('stock_available', 0) > 0 else "Out of Stock"
                        embed.add_field(
                            name=f"{i}. {stock_status} {match.get('name')}",
                            value=f"ID: {match.get('id')} | {match.get('points_required')} pts | Stock: {match.get('stock_available')}",
                            inline=False
                        )
                    
                    embed.add_field(
                        name="💡 How to Fix",
                        value=f"Be more specific with the reward name:\n"
                              f"• Use the full name: `{matches[0].get('name')}`\n"
                              f"• Use unique words: `{self.get_unique_words(matches)}`\n"
                              f"• Use quotes for exact match: `\"{reward_name}\"`",
                        inline=False
                    )
                    await ctx.send(embed=embed)
                    return
                
                # Single match found - proceed
                reward = matches[0]
                current_stock = reward.get('stock_available', 0)
                
                # Check current status
                if action == "enable" and current_stock > 0:
                    await ctx.send(f"✅ {reward.get('name')} is already in stock!")
                    return
                elif action == "disable" and current_stock == 0:
                    await ctx.send(f"❌ {reward.get('name')} is already out of stock!")
                    return
                
                # Perform the action using stock management
                new_stock = 10 if action == "enable" else 0  # Default stock when enabling
                
                async with session.patch(
                    f"{BACKEND_API_URL}/api/incentives/{reward.get('id')}/",
                    json={"stock_available": new_stock},
                    headers={"Authorization": f"Bearer {BOT_SHARED_SECRET}"},
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        await ctx.send(f"❌ Failed to {action} reward: {text[:200]}")
                        return
                    data = await resp.json()
                
                # Clear cache after stock update
                async with session.post(
                    f"{BACKEND_API_URL}/api/incentives/clear_cache/",
                    headers={"Authorization": f"Bearer {BOT_SHARED_SECRET}"},
                ) as cache_resp:
                    pass  # Don't fail if cache clear fails
                
                # Success response
                status_emoji = "✅" if new_stock > 0 else "❌"
                status_text = "in stock" if new_stock > 0 else "out of stock"
                color = 0x00ff00 if new_stock > 0 else 0xff0000
                
                embed = discord.Embed(
                    title=f"{status_emoji} Reward {action_past_tense.title()}",
                    description=f"**{data.get('name')}** is now {status_text}",
                    color=color
                )
                embed.add_field(name="Points Required", value=f"{data.get('points_required')} pts", inline=True)
                embed.add_field(name="Stock Available", value=f"{new_stock}", inline=True)
                embed.add_field(name="Previous Stock", value=f"{current_stock}", inline=True)
                embed.add_field(name="Match Type", value=match_type.title(), inline=True)
                
                await ctx.send(embed=embed)
                
        except Exception as e:
            await ctx.send(f"❌ Error {action}ing reward: {str(e)}")

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
            
            # Clear all caches that could be affected by point changes
            await self.clear_user_caches(str(member.id))
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
            
            # Clear all caches that could be affected by point changes
            await self.clear_user_caches(str(member.id))
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
                
                # Clear all caches that could be affected by point changes
                await self.clear_user_caches(str(member.id))
                
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
<<<<<<< HEAD
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

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def rewards(self, ctx):
        """Show all rewards with their stock status and usage guide"""
        try:
            from bot import BACKEND_API_URL, BOT_SHARED_SECRET
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{BACKEND_API_URL}/api/incentives/admin_list/",
                    headers={"Authorization": f"Bearer {BOT_SHARED_SECRET}"},
                ) as resp:
                    if resp.status != 200:
                        await ctx.send("❌ Failed to fetch rewards.")
                        return
                    data = await resp.json()
                    if not data:
                        await ctx.send("No rewards found.")
                        return
        except Exception:
            await ctx.send("❌ Error fetching rewards.")
            return
        
        embed = discord.Embed(
            title="🎁 Rewards Management",
            description="All rewards and their stock status",
            color=0x0099ff
        )
        
        # Group rewards by stock status
        in_stock_rewards = [r for r in data if r.get('stock_available', 0) > 0]
        out_of_stock_rewards = [r for r in data if r.get('stock_available', 0) == 0]
        
        if in_stock_rewards:
            embed.add_field(
                name=f"✅ In Stock ({len(in_stock_rewards)})",
                value="\n".join([f"• {r.get('name')} ({r.get('points_required')} pts) - Stock: {r.get('stock_available')}" for r in in_stock_rewards]),
                inline=False
            )
        
        if out_of_stock_rewards:
            embed.add_field(
                name=f"❌ Out of Stock ({len(out_of_stock_rewards)})",
                value="\n".join([f"• {r.get('name')} ({r.get('points_required')} pts) - Stock: {r.get('stock_available')}" for r in out_of_stock_rewards]),
                inline=False
            )
        
        embed.add_field(
            name="🔧 Commands",
            value="`!enable_reward <name>` - Restock a reward (sets to 10)\n`!disable_reward <name>` - Make out of stock (sets to 0)\n`!set_stock <amount> <name>` - Set specific stock amount",
            inline=False
        )
        
        embed.add_field(
            name="💡 Naming Tips",
            value="• Use full names for exact matches\n• Use unique words for partial matches\n• Use quotes for exact match: `\"Resume Review\"`\n• Examples: `resume`, `template`, `coaching`",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def enable_reward(self, ctx, *, reward_name: str):
        """Enable a reward (restock it)"""
        await self.handle_reward_command(ctx, reward_name, "enable", "restocked")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def disable_reward(self, ctx, *, reward_name: str):
        """Disable a reward (make it out of stock)"""
        await self.handle_reward_command(ctx, reward_name, "disable", "out of stock")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def set_stock(self, ctx, amount: int, *, reward_name: str):
        """Set stock amount for a reward"""
        try:
            from bot import BACKEND_API_URL, BOT_SHARED_SECRET
            async with aiohttp.ClientSession() as session:
                # First find the reward by name
                async with session.get(
                    f"{BACKEND_API_URL}/api/incentives/admin_list/",
                    headers={"Authorization": f"Bearer {BOT_SHARED_SECRET}"},
                ) as resp:
                    if resp.status != 200:
                        await ctx.send("❌ Failed to fetch rewards.")
                        return
                    rewards = await resp.json()
                
                # Smart matching
                matches, match_type = self.find_reward_matches(rewards, reward_name)
                
                if not matches:
                    # No matches found - show suggestions
                    embed = discord.Embed(
                        title="❌ Reward Not Found",
                        description=f"No rewards found matching: `{reward_name}`",
                        color=0xff0000
                    )
                    embed.add_field(
                        name="💡 Tip",
                        value="Use `!rewards` to see all available rewards",
                        inline=False
                    )
                    await ctx.send(embed=embed)
                    return
                
                if len(matches) > 1:
                    # Multiple matches found - show them to admin
                    embed = discord.Embed(
                        title="🔍 Multiple Rewards Found",
                        description=f"Found {len(matches)} rewards matching `{reward_name}`:",
                        color=0xffaa00
                    )
                    
                    for i, match in enumerate(matches, 1):
                        stock_status = "In Stock" if match.get('stock_available', 0) > 0 else "Out of Stock"
                        embed.add_field(
                            name=f"{i}. {stock_status} {match.get('name')}",
                            value=f"ID: {match.get('id')} | {match.get('points_required')} pts | Stock: {match.get('stock_available')}",
                            inline=False
                        )
                    
                    embed.add_field(
                        name="💡 How to Fix",
                        value=f"Be more specific with the reward name:\n"
                              f"• Use the full name: `{matches[0].get('name')}`\n"
                              f"• Use unique words: `{self.get_unique_words(matches)}`",
                        inline=False
                    )
                    await ctx.send(embed=embed)
                    return
                
                # Single match found - proceed
                reward = matches[0]
                old_stock = reward.get('stock_available', 0)
                
                # Update the stock
                async with session.patch(
                    f"{BACKEND_API_URL}/api/incentives/{reward.get('id')}/",
                    json={"stock_available": amount},
                    headers={"Authorization": f"Bearer {BOT_SHARED_SECRET}"},
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        await ctx.send(f"❌ Failed to update stock: {text[:200]}")
                        return
                
                # Clear cache after stock update
                async with session.post(
                    f"{BACKEND_API_URL}/api/incentives/clear_cache/",
                    headers={"Authorization": f"Bearer {BOT_SHARED_SECRET}"},
                ) as cache_resp:
                    pass  # Don't fail if cache clear fails
                
                embed = discord.Embed(
                    title="📦 Stock Updated",
                    description=f"Updated stock for **{reward.get('name')}**",
                    color=0x00ff00
                )
                embed.add_field(name="Reward", value=reward.get('name'), inline=True)
                embed.add_field(name="New Stock", value=str(amount), inline=True)
                embed.add_field(name="Previous Stock", value=str(old_stock), inline=True)
                embed.add_field(name="Points Required", value=f"{reward.get('points_required')} pts", inline=True)
                embed.add_field(name="Match Type", value=match_type.title(), inline=True)
                
                await ctx.send(embed=embed)
                
        except Exception as e:
            await ctx.send(f"❌ Error updating stock: {str(e)}")

async def setup(bot):
    await bot.add_cog(Admin(bot))
