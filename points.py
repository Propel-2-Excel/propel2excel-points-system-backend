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
            return await update_user_points_in_backend(user_id, pts, action)
        except Exception as e:
            print(f"Error syncing points with backend: {e}")
            return False

    async def award_daily_points(self, message):
        """Award daily Discord points and send motivational message if points were actually awarded"""
        user_id = str(message.author.id)
        
        try:
            # Call backend API directly to check response
            response_data = await self.call_backend_api(user_id, "Message sent")
            
            # Only show reward if points were actually awarded (not if daily limit hit)
            if response_data and not response_data.get("already_earned_today", False):
                # Get user's updated total points
                total_points = response_data.get("total_points", 0)
                
                # Create motivational embed
                embed = discord.Embed(
                    title="🎉 Daily Reward Earned!",
                    description=f"Great to see you here, {message.author.display_name}!",
                    color=0x00ff00
                )
                
                embed.add_field(
                    name="💰 Today's Reward",
                    value="**+1 point** for staying active in our community!",
                    inline=False
                )
                
                embed.add_field(
                    name="🏆 Your Total",
                    value=f"**{total_points} points**",
                    inline=True
                )
                
                # Add milestone progress
                next_milestone = self.get_next_milestone(total_points)
                if next_milestone:
                    points_needed = next_milestone['points'] - total_points
                    embed.add_field(
                        name="🎯 Next Goal",
                        value=f"**{points_needed} more** for {next_milestone['name']}",
                        inline=True
                    )
                
                # Add motivational footer
                motivational_messages = [
                    "Every message counts towards your goals! 🚀",
                    "You're building great habits! Keep it up! 💪",
                    "Consistency is key to success! 🌟",
                    "Your engagement helps the whole community grow! 🌱",
                    "Small steps lead to big achievements! ⭐"
                ]
                import random
                embed.set_footer(text=random.choice(motivational_messages))
                
                # Send the reward message
                await message.channel.send(embed=embed)
                
        except Exception as e:
            print(f"Error in award_daily_points: {e}")

    async def call_backend_api(self, user_id, action):
        """Call backend API and return response data"""
        try:
            from bot import BACKEND_API_URL, BOT_SHARED_SECRET
            import aiohttp
            
            # Map free-form actions to Activity.activity_type values
            action_map = {
                "Message sent": "discord_activity",
                "Liking/interacting": "like_interaction",
                "Resume review request": "resume_review_request",
            }
            activity_type = action_map.get(action, "discord_activity")

            payload = {
                "action": "add-activity",
                "discord_id": user_id,
                "activity_type": activity_type,
                "details": action,
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BACKEND_API_URL}/api/bot/",
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Bot-Secret": BOT_SHARED_SECRET,
                    }
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        print(f"Backend API error: {response.status} - {error_text}")
                        return None
                    
        except Exception as e:
            print(f"Error calling backend API: {e}")
            return None

    async def call_backend_api_direct(self, user_id, activity_type, details):
        """Call backend API directly with activity type"""
        try:
            from bot import BACKEND_API_URL, BOT_SHARED_SECRET
            import aiohttp

            payload = {
                "action": "add-activity",
                "discord_id": user_id,
                "activity_type": activity_type,
                "details": details,
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BACKEND_API_URL}/api/bot/",
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Bot-Secret": BOT_SHARED_SECRET,
                    }
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        print(f"Backend API error: {response.status} - {error_text}")
                        return None
                    
        except Exception as e:
            print(f"Error calling backend API direct: {e}")
            return None

    def get_next_milestone(self, current_points):
        """Get the next milestone the user can work towards"""
        milestones = [
            {"points": 50, "name": "Azure Certification"},
            {"points": 75, "name": "Resume Review"},
            {"points": 100, "name": "Hackathon Entry"}
        ]
        
        for milestone in milestones:
            if current_points < milestone["points"]:
                return milestone
        return None  # User has reached all milestones
    
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
        
        # Award points for normal activity and send motivational message
        await self.award_daily_points(message)

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
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def resume(self, ctx):
        """Start resume review process - sends DM with form link and instructions"""
        try:
            form_url = "https://forms.gle/EKHLrqhHwt1bGQjd6"
            
            embed = discord.Embed(
                title="📋 Resume Review Request",
                description="I'll help you get a professional resume review!",
                color=0x0099ff
            )
            embed.add_field(
                name="📝 Next Steps", 
                value="1. Click the form link below\n2. Fill out your details\n3. Upload your resume\n4. Select your target industry\n5. Choose your availability",
                inline=False
            )
            embed.add_field(
                name="🔗 Form Link",
                value=f"[Resume Review Form]({form_url})",
                inline=False
            )
            embed.add_field(
                name="⏰ Sessions",
                value="30-minute slots between 9 AM - 5 PM",
                inline=True
            )
            embed.add_field(
                name="📧 Contact",
                value="Email: propel@propel2excel.com",
                inline=True
            )
            embed.add_field(
                name="💡 Tips",
                value="• Have your resume ready as PDF\n• Be specific about your target role\n• Choose multiple time slots for better matching",
                inline=False
            )
            
            await ctx.author.send(embed=embed)
            await ctx.send(f"✅ {ctx.author.mention} Check your DMs for the resume review form!")
            
            # Record the activity using current backend pattern
            await self.call_backend_api(str(ctx.author.id), "Resume review request")
            
        except discord.Forbidden:
            await ctx.send("❌ I can't send you a DM. Please enable DMs from server members and try again.")
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")
            print(f"Error in resume command: {e}")

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)  # 1 use per 10 seconds per user
    async def event(self, ctx):
        """Mark event attendance for +15 points"""
        try:
            # Call backend API directly
            response_data = await self.call_backend_api_direct(str(ctx.author.id), "event_attendance", "Event attendance")
            
            if response_data:
                total_points = response_data.get("total_points", 0)
                embed = discord.Embed(
                    title="🎉 Event Attendance",
                    description=f"{ctx.author.mention}, you've earned **15 points** for attending the event!",
                    color=0x00ff00
                )
                embed.add_field(name="🏆 Your Total", value=f"**{total_points} points**", inline=True)
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ An error occurred while processing your event attendance.")
        except Exception as e:
            await ctx.send("❌ An error occurred while processing your event attendance.")
            print(f"Error in event command: {e}")

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)  # 1 use per 10 seconds per user
    async def resource(self, ctx, *, description):
        """Share a resource for +10 points"""
        try:
            # Check if user provided a description
            if not description or len(description.strip()) < 10:
                await ctx.send("❌ Please provide a detailed description of your resource (at least 10 characters).\n\n**Usage:** `!resource <description of the resource you want to share>`")
                return
            
            # Call backend API directly to award points immediately
            response_data = await self.call_backend_api_direct(str(ctx.author.id), "resource_share", f"Resource share: {description[:100]}")
            
            if response_data:
                total_points = response_data.get("total_points", 0)
                embed = discord.Embed(
                    title="📚 Resource Shared",
                    description=f"{ctx.author.mention}, you've earned **10 points** for sharing a valuable resource!",
                    color=0x00ff00
                )
                
                embed.add_field(
                    name="📝 Resource",
                    value=description[:500] + "..." if len(description) > 500 else description,
                    inline=False
                )
                
                embed.add_field(name="🏆 Your Total", value=f"**{total_points} points**", inline=True)
                embed.set_footer(text="Thank you for contributing to the community!")
                
                await ctx.send(embed=embed)
                
                # Still notify admins for visibility (optional)
                # await self.notify_admins_of_resource_share(ctx, description)
            else:
                await ctx.send("❌ An error occurred while processing your resource share.")
            
        except Exception as e:
            await ctx.send("❌ An error occurred while processing your resource share.")
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
            # Call backend API directly
            response_data = await self.call_backend_api_direct(str(ctx.author.id), "linkedin_post", "LinkedIn update")
            
            if response_data:
                total_points = response_data.get("total_points", 0)
                embed = discord.Embed(
                    title="💼 LinkedIn Update",
                    description=f"{ctx.author.mention}, you've earned **5 points** for posting a LinkedIn update!",
                    color=0x00ff00
                )
                embed.add_field(name="🏆 Your Total", value=f"**{total_points} points**", inline=True)
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ An error occurred while processing your LinkedIn update.")
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
            embed.add_field(name="📚 Resource Share", value="+10 points", inline=True)
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
                value="Resource description not available",
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
                value="Resource description not available",
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
