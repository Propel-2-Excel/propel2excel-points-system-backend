from discord.ext import commands
import discord
import asyncio
from datetime import datetime, timedelta
import re
import aiohttp
import os

# Milestone definitions for incentives
MILESTONES = {
    50: "Azure Certification",
    75: "Resume Review", 
    100: "Hackathon"
}

class Points(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.processed_messages = set()  # Track processed messages to prevent duplicates

    def add_points(self, user_id, pts, action):
        """Forward all point awards to backend; no local DB writes."""
        try:
            asyncio.create_task(self.sync_points_with_backend(user_id, pts, action))
        except Exception as e:
            print(f"Error adding points: {e}")

    async def sync_points_with_backend(self, user_id, pts, action):
        """Sync points with backend API"""
        try:
            from bot import update_user_points_in_backend
            await update_user_points_in_backend(user_id, pts, action)
        except Exception as e:
            print(f"Error syncing points with backend: {e}")
    
    async def fetch_user_total_points(self, discord_id: str) -> int:
        """Fetch user's total points from backend via /api/bot summary."""
        try:
            from bot import BACKEND_API_URL, BOT_SHARED_SECRET
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BACKEND_API_URL}/api/bot/",
                    json={"action": "summary", "discord_id": discord_id, "limit": 1},
                    headers={"Content-Type": "application/json", "X-Bot-Secret": BOT_SHARED_SECRET},
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return int(data.get("total_points", 0))
        except Exception:
            pass
        return 0

    async def fetch_user_recent_logs(self, discord_id: str):
        try:
            from bot import BACKEND_API_URL, BOT_SHARED_SECRET
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BACKEND_API_URL}/api/bot/",
                    json={"action": "summary", "discord_id": discord_id, "limit": 10},
                    headers={"Content-Type": "application/json", "X-Bot-Secret": BOT_SHARED_SECRET},
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        logs = data.get("recent_logs", [])
                        # Return tuples (action, pts, ts) to match embed usage
                        return [(item.get("action"), item.get("points", 0), item.get("timestamp", "")) for item in logs]
        except Exception:
            pass
        return []

    async def fetch_user_milestones(self, discord_id: str):
        try:
            from bot import BACKEND_API_URL, BOT_SHARED_SECRET
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BACKEND_API_URL}/api/bot/",
                    json={"action": "summary", "discord_id": discord_id, "limit": 1},
                    headers={"Content-Type": "application/json", "X-Bot-Secret": BOT_SHARED_SECRET},
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        current_points = int(data.get("total_points", 0))
                        unlocks = data.get("unlocks", [])
                        achieved = [item.get("name") for item in unlocks]
                        return current_points, achieved
        except Exception:
            pass
        return 0, []

    async def check_milestones(self, user_id, total_points):
        """Send congratulatory DM when thresholds crossed (no local DB)."""
        try:
            for points_required, milestone_name in MILESTONES.items():
                if total_points >= points_required:
                    await self.send_milestone_dm(user_id, milestone_name, points_required)
        except Exception as e:
            print(f"Error checking milestones: {e}")

    async def send_milestone_dm(self, user_id, milestone_name, points_required):
        """Send a congratulatory DM to user for reaching a milestone"""
        try:
            user = self.bot.get_user(int(user_id))
            if user:
                embed = discord.Embed(
                    title="🎉 Congratulations! You've Unlocked a New Incentive!",
                    description=f"You've reached **{points_required} points** and unlocked:",
                    color=0x00ff00
                )
                
                embed.add_field(
                    name=f"🏆 {milestone_name}",
                    value="You can now redeem this incentive!",
                    inline=False
                )
                
                embed.add_field(
                    name="Current Points",
                    value=f"**{points_required}+ points**",
                    inline=True
                )
                
                embed.add_field(
                    name="Next Steps",
                    value="Contact an admin to redeem your incentive!",
                    inline=True
                )
                
                embed.set_footer(text="Keep earning points to unlock more incentives!")
                
                await user.send(embed=embed)
                print(f"Sent milestone DM to {user.name} for {milestone_name}")
            else:
                print(f"Could not find user {user_id} to send milestone DM")
                
        except Exception as e:
            print(f"Error sending milestone DM to {user_id}: {e}")

    @commands.Cog.listener()
    async def on_message(self, message):
        # Prevent processing bot messages
        if message.author.bot:
            return
        
        # Prevent processing bot commands
        if message.content.startswith('!'):
            return
        
        # Prevent duplicate processing
        message_id = f"{message.id}_{message.author.id}"
        if message_id in self.processed_messages:
            return
        
        # Mark message as processed
        self.processed_messages.add(message_id)
        
        # Clean up old processed messages (keep only last 1000)
        if len(self.processed_messages) > 1000:
            self.processed_messages.clear()
        
        user_id = str(message.author.id)
        
        # Award points for normal activity (only for non-command messages)
        self.add_points(user_id, 1, "Message sent")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        
        user_id = str(user.id)
        self.add_points(user_id, 2, "Liking/interacting")

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)  # 1 use per 3 seconds per user
    async def points(self, ctx):
        try:
            total = await self.fetch_user_total_points(str(ctx.author.id))
            embed = discord.Embed(
                title="💰 Points Status",
                description=f"{ctx.author.mention}'s point information",
                color=0x00ff00
            )
            embed.add_field(name="Current Points", value=f"**{total}** points", inline=True)
            embed.add_field(name="Status", value="✅ Good standing", inline=True)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send("❌ An error occurred while fetching your points. Please try again later.")
            print(f"Error in points command: {e}")

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)  # 1 use per 5 seconds per user
    async def pointshistory(self, ctx):
        try:
            rows = await self.fetch_user_recent_logs(str(ctx.author.id))
            
            if not rows:
                await ctx.send(f"{ctx.author.mention}, you have no point activity yet.")
                return
            
            embed = discord.Embed(
                title="📊 Point History",
                description=f"Last 10 point actions for {ctx.author.mention}",
                color=0x0099ff
            )
            
            for action, pts, ts in rows:
                embed.add_field(
                    name=f"{ts[:19]}",
                    value=f"{action} (+{pts} pts)",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send("❌ An error occurred while fetching your point history.")
            print(f"Error in pointshistory command: {e}")

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)  # 1 use per 10 seconds per user
    async def resume(self, ctx):
        """Upload resume for +20 points"""
        try:
            self.add_points(str(ctx.author.id), 20, "Resume upload")
            embed = discord.Embed(
                title="📄 Resume Upload",
                description=f"{ctx.author.mention}, you've earned **20 points** for uploading your resume!",
                color=0x00ff00
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send("❌ An error occurred while processing your resume upload.")
            print(f"Error in resume command: {e}")

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)  # 1 use per 10 seconds per user
    async def event(self, ctx):
        """Mark event attendance for +15 points"""
        try:
            self.add_points(str(ctx.author.id), 15, "Event attendance")
            embed = discord.Embed(
                title="🎉 Event Attendance",
                description=f"{ctx.author.mention}, you've earned **15 points** for attending the event!",
                color=0x00ff00
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send("❌ An error occurred while processing your event attendance.")
            print(f"Error in event command: {e}")

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)  # 1 use per 10 seconds per user
    async def resource(self, ctx, *, description):
        """Submit a resource for admin review and potential points"""
        try:
            # Check if user provided a description
            if not description or len(description.strip()) < 10:
                await ctx.send("❌ Please provide a detailed description of your resource (at least 10 characters).\n\n**Usage:** `!resource <description of the resource you want to share>`")
                return
            
            # For MVP, do not persist local resource submissions; just notify admins
            
            # Create submission confirmation embed
            embed = discord.Embed(
                title="📚 Resource Submission Received",
                description=f"{ctx.author.mention}, your resource has been submitted for admin review!",
                color=0x0099ff
            )
            
            embed.add_field(
                name="📝 Description",
                value=description[:1000] + "..." if len(description) > 1000 else description,
                inline=False
            )
            
            embed.add_field(
                name="⏳ Status",
                value="🔄 **Pending Review**",
                inline=True
            )
            
            embed.add_field(
                name="🎯 Potential Reward",
                value="**10 points** (if approved)",
                inline=True
            )
            
            embed.add_field(
                name="📋 Next Steps",
                value="An admin will review your submission and award points if approved. You'll be notified of the decision!",
                inline=False
            )
            
            embed.set_footer(text="Thank you for contributing to the community!")
            
            await ctx.send(embed=embed)
            
            # Notify admins about the new submission
            await self.notify_admins_of_submission(ctx, description)
            
        except Exception as e:
            await ctx.send("❌ An error occurred while submitting your resource. Please try again.")
            print(f"Error in resource command: {e}")

    async def notify_admins_of_submission(self, ctx, description):
        """Notify admins about a new resource submission"""
        try:
            # Get all admins in the server
            admins = [member for member in ctx.guild.members if member.guild_permissions.administrator]
            
            if not admins:
                return
            
            # Create admin notification embed
            embed = discord.Embed(
                title="📚 New Resource Submission",
                description=f"**{ctx.author.display_name}** has submitted a resource for review:",
                color=0xff9900
            )
            
            embed.add_field(
                name="👤 Submitted By",
                value=f"{ctx.author.mention} ({ctx.author.id})",
                inline=True
            )
            
            embed.add_field(
                name="📅 Submitted At",
                value=f"<t:{int(ctx.message.created_at.timestamp())}:F>",
                inline=True
            )
            
            embed.add_field(
                name="📝 Description",
                value=description[:1000] + "..." if len(description) > 1000 else description,
                inline=False
            )
            
            embed.add_field(
                name="🔧 Admin Actions",
                value="Use `!approveresource <user_id> <points> [notes]` to approve\nUse `!rejectresource <user_id> [reason]` to reject",
                inline=False
            )
            
            # Send to each admin
            for admin in admins:
                try:
                    await admin.send(embed=embed)
                except discord.Forbidden:
                    # Admin has DMs disabled, skip
                    continue
                    
        except Exception as e:
            print(f"Error notifying admins: {e}")

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)  # 1 use per 10 seconds per user
    async def linkedin(self, ctx):
        """Post LinkedIn update for +5 points"""
        try:
            self.add_points(str(ctx.author.id), 5, "LinkedIn update")
            embed = discord.Embed(
                title="💼 LinkedIn Update",
                description=f"{ctx.author.mention}, you've earned **5 points** for posting a LinkedIn update!",
                color=0x00ff00
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send("❌ An error occurred while processing your LinkedIn update.")
            print(f"Error in linkedin command: {e}")

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)  # 1 use per 5 seconds per user
    async def pointvalues(self, ctx):
        """Show point values for different actions"""
        try:
            embed = discord.Embed(
                title="🎯 Point Values",
                description="Here are the points you can earn for different actions:",
                color=0x00ff00
            )
            embed.add_field(name="📄 Resume Upload", value="+20 points", inline=True)
            embed.add_field(name="🎉 Event Attendance", value="+15 points", inline=True)
            embed.add_field(name="📚 Resource Share", value="+10 points (after admin review)", inline=True)
            embed.add_field(name="💼 LinkedIn Update", value="+5 points", inline=True)
            embed.add_field(name="👍 Liking/Interacting", value="+2 points", inline=True)
            embed.add_field(name="💬 Message Sent", value="+1 points", inline=True)
            
            embed.set_footer(text="Use the commands: !resume, !event, !resource <description>, !linkedin to claim points!")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send("❌ An error occurred while fetching point values.")
            print(f"Error in pointvalues command: {e}")

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)  # 1 use per 5 seconds per user
    async def milestones(self, ctx):
        """Show available milestones and user's progress"""
        try:
            current_points, achieved_milestones = await self.fetch_user_milestones(str(ctx.author.id))
            
            embed = discord.Embed(
                title="🏆 Available Incentives & Milestones",
                description=f"{ctx.author.mention}'s progress towards unlocking incentives:",
                color=0x0099ff
            )
            
            embed.add_field(
                name="Current Points",
                value=f"**{current_points} points**",
                inline=False
            )
            
            # Show each milestone with status
            for points_required, milestone_name in sorted(MILESTONES.items()):
                status = "✅ Unlocked" if milestone_name in achieved_milestones else "🔒 Locked"
                progress = f"{current_points}/{points_required} points"
                
                embed.add_field(
                    name=f"{milestone_name} ({points_required} pts)",
                    value=f"{status}\n{progress}",
                    inline=True
                )
            
            embed.set_footer(text="Keep earning points to unlock more incentives!")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send("❌ An error occurred while fetching milestone information.")
            print(f"Error in milestones command: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def checkmilestones(self, ctx, user: discord.Member = None):
        """Admin command to manually check milestones for a user"""
        try:
            target_user = user or ctx.author
            user_id = str(target_user.id)
            current_points = await self.fetch_user_total_points(user_id)
            
            await self.check_milestones(user_id, current_points)
            
            embed = discord.Embed(
                title="🔍 Milestone Check Complete",
                description=f"Checked milestones for {target_user.mention}",
                color=0x00ff00
            )
            embed.add_field(name="Current Points", value=f"{current_points} points", inline=True)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send("❌ An error occurred while checking milestones.")
            print(f"Error in checkmilestones command: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def approveresource(self, ctx, user_id: str, points: int, *, notes: str = ""):
        """Approve a resource submission and award points"""
        try:
            submission = None  # backend workflow not implemented yet
            if not submission:
                await ctx.send(f"❌ No pending resource submissions found for user ID: {user_id}")
                return
            # Award via backend
            self.add_points(user_id, points, f"Resource share approved by {ctx.author.display_name}")
            
            # Create approval embed
            embed = discord.Embed(
                title="✅ Resource Approved!",
                description=f"Resource submission has been approved and points awarded!",
                color=0x00ff00
            )
            
            embed.add_field(
                name="👤 User",
                value=f"<@{user_id}>",
                inline=True
            )
            
            embed.add_field(
                name="🎯 Points Awarded",
                value=f"**{points} points**",
                inline=True
            )
            
            embed.add_field(
                name="👨‍⚖️ Reviewed By",
                value=ctx.author.display_name,
                inline=True
            )
            
            embed.add_field(
                name="📝 Description",
                value=description[:500] + "..." if len(description) > 500 else description,
                inline=False
            )
            
            if notes:
                embed.add_field(
                    name="📋 Review Notes",
                    value=notes,
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
            # Notify the user about the approval
            await self.notify_user_of_approval(user_id, points, notes)
            
        except Exception as e:
            await ctx.send(f"❌ Error approving resource: {e}")
            print(f"Error in approveresource command: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def rejectresource(self, ctx, user_id: str, *, reason: str = "No reason provided"):
        """Reject a resource submission"""
        try:
            submission = None
            if not submission:
                await ctx.send(f"❌ No pending resource submissions found for user_id: {user_id}")
                return
            
            # Create rejection embed
            embed = discord.Embed(
                title="❌ Resource Rejected",
                description=f"Resource submission has been rejected.",
                color=0xff0000
            )
            
            embed.add_field(
                name="👤 User",
                value=f"<@{user_id}>",
                inline=True
            )
            
            embed.add_field(
                name="👨‍⚖️ Reviewed By",
                value=ctx.author.display_name,
                inline=True
            )
            
            embed.add_field(
                name="📝 Description",
                value=description[:500] + "..." if len(description) > 500 else description,
                inline=False
            )
            
            embed.add_field(
                name="❌ Rejection Reason",
                value=reason,
                inline=False
            )
            
            await ctx.send(embed=embed)
            
            # Notify the user about the rejection
            await self.notify_user_of_rejection(user_id, reason)
            
        except Exception as e:
            await ctx.send(f"❌ Error rejecting resource: {e}")
            print(f"Error in rejectresource command: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def pendingresources(self, ctx):
        """Show all pending resource submissions"""
        try:
            submissions = []  # not yet implemented
            
            if not submissions:
                await ctx.send("✅ No pending resource submissions!")
                return
            
            embed = discord.Embed(
                title="📚 Pending Resource Submissions",
                description=f"Found **{len(submissions)}** pending submissions:",
                color=0xff9900
            )
            
            for i, (user_id, description, submitted_at, submission_id) in enumerate(submissions[:10], 1):
                embed.add_field(
                    name=f"#{i} - <@{user_id}>",
                    value=f"**Submitted:** <t:{int(datetime.fromisoformat(submitted_at).timestamp())}:R>\n**Description:** {description[:200]}...\n**ID:** {submission_id}",
                    inline=False
                )
            
            if len(submissions) > 10:
                embed.set_footer(text=f"And {len(submissions) - 10} more submissions...")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error fetching pending resources: {e}")
            print(f"Error in pendingresources command: {e}")

    async def notify_user_of_approval(self, user_id: str, points: int, notes: str):
        """Notify user that their resource was approved"""
        try:
            user = self.bot.get_user(int(user_id))
            if user:
                embed = discord.Embed(
                    title="🎉 Your Resource Was Approved!",
                    description="Congratulations! Your resource submission has been approved!",
                    color=0x00ff00
                )
                
                embed.add_field(
                    name="🎯 Points Awarded",
                    value=f"**{points} points**",
                    inline=True
                )
                
                embed.add_field(
                    name="✅ Status",
                    value="**Approved**",
                    inline=True
                )
                
                if notes:
                    embed.add_field(
                        name="📋 Admin Notes",
                        value=notes,
                        inline=False
                    )
                
                embed.set_footer(text="Thank you for contributing to the community!")
                
                await user.send(embed=embed)
                
        except Exception as e:
            print(f"Error notifying user of approval: {e}")

    async def notify_user_of_rejection(self, user_id: str, reason: str):
        """Notify user that their resource was rejected"""
        try:
            user = self.bot.get_user(int(user_id))
            if user:
                embed = discord.Embed(
                    title="❌ Resource Submission Rejected",
                    description="Your resource submission has been reviewed and rejected.",
                    color=0xff0000
                )
                
                embed.add_field(
                    name="❌ Reason",
                    value=reason,
                    inline=False
                )
                
                embed.add_field(
                    name="💡 Tips",
                    value="• Make sure your resource is relevant and valuable\n• Provide a clear, detailed description\n• Ensure the resource is accessible and legitimate\n• Try submitting a different resource!",
                    inline=False
                )
                
                embed.set_footer(text="Don't give up! Try submitting another resource.")
                
                await user.send(embed=embed)
                
        except Exception as e:
            print(f"Error notifying user of rejection: {e}")

async def setup(bot):
    await bot.add_cog(Points(bot))
