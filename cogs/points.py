from discord.ext import commands
import discord
import asyncio
from datetime import datetime, timedelta
import re
import aiohttp
import os

# Modal classes for admin interactions
class ApprovalModal(discord.ui.Modal):
    def __init__(self, submission_type, submission_id, user_id, description, bot_instance, action_type):
        super().__init__(title=f"Approve {submission_type}")
        self.submission_type = submission_type
        self.submission_id = submission_id
        self.user_id = user_id
        self.description = description
        self.bot_instance = bot_instance
        self.action_type = action_type
        
        # Set default points based on submission type
        default_points = "10"  # Default fallback
        if submission_type.lower() == "event":
            default_points = "15"
        elif submission_type.lower() == "resource":
            default_points = "10"
        elif submission_type.lower() == "linkedin":
            default_points = "5"
        
        # Add points input
        self.points_input = discord.ui.TextInput(
            label="Points to Award",
            placeholder=f"Enter points (default: {default_points})",
            default=default_points,
            required=True,
            max_length=3
        )
        self.add_item(self.points_input)
        
        # Add notes input
        self.notes_input = discord.ui.TextInput(
            label="Admin Notes (Optional)",
            placeholder="Add any notes about this approval...",
            required=False,
            max_length=500,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.notes_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            points = int(self.points_input.value)
            notes = self.notes_input.value or ""
            
            # Call the appropriate approval method based on submission type
            if self.submission_type.lower() == "resource":
                success, result = await self.bot_instance.approve_resource_backend(self.submission_id, points, notes)
            elif self.submission_type.lower() == "event":
                success, result = await self.bot_instance.approve_event_backend(self.submission_id, points, notes)
            elif self.submission_type.lower() == "linkedin":
                success, result = await self.bot_instance.approve_linkedin_backend(self.submission_id, points, notes)
            else:
                await interaction.response.send_message("❌ Unknown submission type.", ephemeral=True)
                return
            
            if success:
                # Update the original embed to show approval
                embed = discord.Embed(
                    title=f"✅ {self.submission_type} Approved!",
                    description=f"Approved by {interaction.user.display_name}",
                    color=0x00ff00
                )
                embed.add_field(name="Points Awarded", value=f"{points} points", inline=True)
                embed.add_field(name="Reviewed By", value=interaction.user.display_name, inline=True)
                if notes:
                    embed.add_field(name="Notes", value=notes, inline=False)
                
                # Disable all buttons in the original message
                disabled_view = discord.ui.View()
                disabled_view.add_item(discord.ui.Button(label="Approved", style=discord.ButtonStyle.green, disabled=True, emoji="✅"))
                disabled_view.add_item(discord.ui.Button(label="Rejected", style=discord.ButtonStyle.red, disabled=True, emoji="❌"))
                
                await interaction.message.edit(view=disabled_view)
                await interaction.response.send_message(embed=embed)
                
                # Notify the user
                await self.bot_instance.notify_user_of_approval(self.user_id, points, notes)
            else:
                await interaction.response.send_message(f"❌ Failed to approve: {result}", ephemeral=True)
                
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number for points.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error approving submission: {e}", ephemeral=True)

class RejectionModal(discord.ui.Modal):
    def __init__(self, submission_type, submission_id, user_id, description, bot_instance):
        super().__init__(title=f"Reject {submission_type}")
        self.submission_type = submission_type
        self.submission_id = submission_id
        self.user_id = user_id
        self.description = description
        self.bot_instance = bot_instance
        
        # Add reason input
        self.reason_input = discord.ui.TextInput(
            label="Rejection Reason",
            placeholder="Enter reason for rejection...",
            required=True,
            max_length=500,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.reason_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            reason = self.reason_input.value
            
            # Call the appropriate rejection method based on submission type
            if self.submission_type.lower() == "resource":
                success, result = await self.bot_instance.reject_resource_backend(self.submission_id, reason)
            elif self.submission_type.lower() == "event":
                success, result = await self.bot_instance.reject_event_backend(self.submission_id, reason)
            elif self.submission_type.lower() == "linkedin":
                success, result = await self.bot_instance.reject_linkedin_backend(self.submission_id, reason)
            else:
                await interaction.response.send_message("❌ Unknown submission type.", ephemeral=True)
                return
            
            if success:
                # Update the original embed to show rejection
                embed = discord.Embed(
                    title=f"❌ {self.submission_type} Rejected",
                    description=f"Rejected by {interaction.user.display_name}",
                    color=0xff0000
                )
                embed.add_field(name="Reason", value=reason, inline=False)
                
                # Disable all buttons in the original message
                disabled_view = discord.ui.View()
                disabled_view.add_item(discord.ui.Button(label="Approved", style=discord.ButtonStyle.green, disabled=True, emoji="✅"))
                disabled_view.add_item(discord.ui.Button(label="Rejected", style=discord.ButtonStyle.red, disabled=True, emoji="❌"))
                
                await interaction.message.edit(view=disabled_view)
                await interaction.response.send_message(embed=embed)
                
                # Notify the user
                await self.bot_instance.notify_user_of_rejection(self.user_id, reason)
            else:
                await interaction.response.send_message(f"❌ Failed to reject: {result}", ephemeral=True)
                
        except Exception as e:
            await interaction.response.send_message(f"❌ Error rejecting submission: {e}", ephemeral=True)


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
        # Use smart backend URL detection (same logic as bot.py)
        explicit_url = os.getenv('BACKEND_API_URL')
        if explicit_url:
            self.backend_api_url = explicit_url
        elif os.getenv('RENDER'):
            port = os.getenv('PORT', '8000')
            self.backend_api_url = f'http://127.0.0.1:{port}'
        else:
            self.backend_api_url = 'http://localhost:8000'
        self.bot_shared_secret = os.getenv('BOT_SHARED_SECRET', '')

    async def _backend_request(self, payload):
        """Make a request to the backend API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.backend_api_url}/api/bot/",
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Bot-Secret": self.bot_shared_secret,
                    }
                ) as response:
                    if response.status in (200, 201):  # 200 = OK, 201 = Created
                        return await response.json()
                    else:
                        error_text = await response.text()
                        print(f"Backend API error: {response.status} - {error_text}")
                        return None
        except Exception as e:
            print(f"Error calling backend API: {e}")
            return None

    def add_points(self, user_id, pts, action):
        """Forward all point awards to backend; no local DB writes."""
        try:
            asyncio.create_task(self.sync_points_with_backend(user_id, pts, action))
        except Exception as e:
            print(f"Error adding points: {e}")

    async def sync_points_with_backend(self, user_id, pts, action):
        """Sync points with backend API"""
        try:
            return await self._backend_request({
                "action": "add-activity",
                "discord_id": user_id,
                "activity_type": "discord_activity",
                "details": action,
            })
        except Exception as e:
            print(f"Error syncing points with backend: {e}")
            return False

    async def submit_resource_to_backend(self, discord_id, description):
        """Submit resource to backend API and return submission ID"""
        try:
            payload = {
                "action": "submit-resource",
                "discord_id": discord_id,
                "description": description,
            }
            
            response = await self._backend_request(payload)
            if response and response.get("success"):
                return True, response.get("submission_id")
            return False, None
                        
        except Exception as e:
            print(f"Error submitting resource to backend: {e}")
            return False, None

    async def approve_resource_backend(self, submission_id, points, notes):
        """Approve resource via backend API"""
        try:
            payload = {
                "action": "approve-resource",
                "submission_id": submission_id,
                "points": points,
                "notes": notes,
            }
            
            response = await self._backend_request(payload)
            if response:
                return True, response
            else:
                return False, "Failed to approve resource"
                        
        except Exception as e:
            return False, str(e)

    async def reject_resource_backend(self, submission_id, reason):
        """Reject resource via backend API"""
        try:
            payload = {
                "action": "reject-resource",
                "submission_id": submission_id,
                "reason": reason,
            }
            
            response = await self._backend_request(payload)
            if response:
                return True, response
            else:
                return False, "Failed to reject resource"
                        
        except Exception as e:
            return False, str(e)

    async def submit_event_to_backend(self, discord_id, event_name):
        """Submit event to backend API and return submission ID"""
        try:
            payload = {
                "action": "submit-event",
                "discord_id": discord_id,
                "event_name": event_name,
            }
            
            response = await self._backend_request(payload)
            if response and response.get("success"):
                return True, response.get("submission_id")
            return False, None
                        
        except Exception as e:
            print(f"Error submitting event to backend: {e}")
            return False, None

    async def submit_linkedin_to_backend(self, discord_id, description):
        """Submit LinkedIn update to backend API and return submission ID"""
        try:
            payload = {
                "action": "submit-linkedin",
                "discord_id": discord_id,
                "description": description,
            }
            
            response = await self._backend_request(payload)
            if response and response.get("success"):
                return True, response.get("submission_id")
            return False, None
                        
        except Exception as e:
            print(f"Error submitting LinkedIn update to backend: {e}")
            return False, None

    async def approve_event_backend(self, submission_id, points, notes):
        """Approve event via backend API"""
        try:
            payload = {
                "action": "approve-event",
                "submission_id": submission_id,
                "points": points,
                "notes": notes,
            }
            
            response = await self._backend_request(payload)
            if response:
                return True, response
            else:
                return False, "Failed to approve event"
                        
        except Exception as e:
            return False, str(e)

    async def reject_event_backend(self, submission_id, reason):
        """Reject event via backend API"""
        try:
            payload = {
                "action": "reject-event",
                "submission_id": submission_id,
                "reason": reason,
            }
            
            response = await self._backend_request(payload)
            if response:
                return True, response
            else:
                return False, "Failed to reject event"
                        
        except Exception as e:
            return False, str(e)

    async def approve_linkedin_backend(self, submission_id, points, notes):
        """Approve LinkedIn via backend API"""
        try:
            payload = {
                "action": "approve-linkedin",
                "submission_id": submission_id,
                "points": points,
                "notes": notes,
            }
            
            response = await self._backend_request(payload)
            if response:
                return True, response
            else:
                return False, "Failed to approve LinkedIn update"
                        
        except Exception as e:
            return False, str(e)

    async def reject_linkedin_backend(self, submission_id, reason):
        """Reject LinkedIn via backend API"""
        try:
            payload = {
                "action": "reject-linkedin",
                "submission_id": submission_id,
                "reason": reason,
            }
            
            response = await self._backend_request(payload)
            if response:
                return True, response
            else:
                return False, "Failed to reject LinkedIn update"
                        
        except Exception as e:
            return False, str(e)

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
            
            return await self._backend_request(payload)
                    
        except Exception as e:
            print(f"Error calling backend API: {e}")
            return None

    async def call_backend_api_direct(self, user_id, activity_type, details):
        """Call backend API directly with activity type"""
        try:
            payload = {
                "action": "add-activity",
                "discord_id": user_id,
                "activity_type": activity_type,
                "details": details,
            }
            
            return await self._backend_request(payload)
                    
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
            response = await self._backend_request({
                "action": "summary", 
                "discord_id": discord_id, 
                "limit": 1
            })
            if response:
                return int(response.get("total_points", 0))
        except Exception:
            pass
        return 0

    async def fetch_user_recent_logs(self, discord_id: str):
        try:
            response = await self._backend_request({
                "action": "summary", 
                "discord_id": discord_id, 
                "limit": 10
            })
            if response:
                logs = response.get("recent_logs", [])
                # Return tuples (action, pts, ts) to match embed usage
                return [(item.get("action"), item.get("points", 0), item.get("timestamp", "")) for item in logs]
        except Exception:
            pass
        return []

    async def fetch_user_milestones(self, discord_id: str):
        try:
            response = await self._backend_request({
                "action": "summary", 
                "discord_id": discord_id, 
                "limit": 1
            })
            if response:
                current_points = int(response.get("total_points", 0))
                unlocks = response.get("unlocks", [])
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
    async def on_ready(self):
        """Start hourly admin reports when bot is ready"""
        if not hasattr(self, '_hourly_reports_started'):
            self._hourly_reports_started = True
            # Start the hourly reports task
            import asyncio
            asyncio.create_task(self.start_hourly_reports())
            print("🕐 Hourly admin reports started (8 AM - 8 PM EST)")

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
    async def event(self, ctx, *, description: str = ""):
        """Submit event attendance for admin review and potential points
        
        Usage: !event <description> (with photo attachment)
        Example: !event "Attended the Python workshop on web scraping and learned about beautiful soup"
        """
        try:
            # Check if user provided a description
            if not description:
                embed = discord.Embed(
                    title="❌ Missing Event Description",
                    description="Please provide a description of the event you attended.",
                    color=0xff0000
                )
                embed.add_field(
                    name="📝 Usage",
                    value="`!event <description>` (with photo attachment)",
                    inline=False
                )
                embed.add_field(
                    name="💡 Example",
                    value="`!event \"Attended the Python workshop on web scraping and learned about beautiful soup\"`",
                    inline=False
                )
                embed.add_field(
                    name="📋 What to Include",
                    value="• What event you attended\n• What you learned or gained\n• Why it was valuable",
                    inline=False
                )
                embed.add_field(
                    name="📸 Photo Required",
                    value="**You must attach a photo/screenshot** to prove your attendance!",
                    inline=False
                )
                await ctx.send(embed=embed)
                return
            
            # Check if description is too short
            if len(description) < 15:
                embed = discord.Embed(
                    title="❌ Description Too Short",
                    description="Please provide a more detailed description (at least 15 characters).",
                    color=0xff0000
                )
                embed.add_field(
                    name="📝 Current Description",
                    value=f"\"{description}\"",
                    inline=False
                )
                embed.add_field(
                    name="💡 Make it Better",
                    value="• Add what event you attended\n• Explain what you learned\n• Mention why it was valuable",
                    inline=False
                )
                embed.add_field(
                    name="📋 Example",
                    value="`!event \"Attended the comprehensive Python workshop that taught web scraping with beautiful soup and requests libraries\"`",
                    inline=False
                )
                await ctx.send(embed=embed)
                return
            
            # Check if user attached a photo
            if not ctx.message.attachments:
                embed = discord.Embed(
                    title="❌ Photo Required",
                    description="You must attach a photo/screenshot to prove your event attendance.",
                    color=0xff0000
                )
                embed.add_field(
                    name="📸 What to Attach",
                    value="• Screenshot of the event (virtual events)\n• Photo at the event location\n• Certificate of attendance\n• Event registration confirmation",
                    inline=False
                )
                embed.add_field(
                    name="💡 How to Attach",
                    value="1. Take a photo/screenshot\n2. Drag and drop it into Discord\n3. Type your `!event` command",
                    inline=False
                )
                embed.add_field(
                    name="📋 Example",
                    value="`!event \"Attended the Python workshop on web scraping\"` (with photo attached)",
                    inline=False
                )
                await ctx.send(embed=embed)
                return
            
            # Validate the attached image
            attachment = ctx.message.attachments[0]
            
            # Check file size (max 8MB for Discord)
            if attachment.size > 8 * 1024 * 1024:
                embed = discord.Embed(
                    title="❌ Image Too Large",
                    description="The attached image is too large. Please use an image smaller than 8MB.",
                    color=0xff0000
                )
                embed.add_field(
                    name="📸 Try Again",
                    value="• Compress the image\n• Take a new screenshot\n• Use a smaller photo",
                    inline=False
                )
                await ctx.send(embed=embed)
                return
            
            # Check if it's a valid image type
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            if not any(attachment.filename.lower().endswith(ext) for ext in valid_extensions):
                embed = discord.Embed(
                    title="❌ Invalid Image Format",
                    description="Please attach a valid image file (JPG, PNG, GIF, or WebP).",
                    color=0xff0000
                )
                embed.add_field(
                    name="📸 Supported Formats",
                    value="• JPG/JPEG\n• PNG\n• GIF\n• WebP",
                    inline=False
                )
                await ctx.send(embed=embed)
                return
            
            # Combine description with image info for backend submission
            image_info = f"Image: {attachment.filename} ({attachment.size} bytes)"
            full_description = f"{description}\n\n{image_info}"
            
            # Submit event to backend
            success, submission_id = await self.submit_event_to_backend(str(ctx.author.id), full_description)
            
            if not success:
                await ctx.send("❌ Failed to submit event attendance to backend. Please try again later.")
                return
            
            # Create submission confirmation embed
            embed = discord.Embed(
                title="🎉 Event Attendance Submitted",
                description=f"{ctx.author.mention}, your event attendance has been submitted for admin review!",
                color=0x0099ff
            )
            
            embed.add_field(
                name="📝 Event Description",
                value=f"**{description[:200]}{'...' if len(description) > 200 else ''}**",
                inline=False
            )
            
            embed.add_field(
                name="📸 Proof Attached",
                value=f"✅ **{attachment.filename}**",
                inline=True
            )
            
            embed.add_field(
                name="⏳ Status",
                value="🔄 **Pending Review**",
                inline=True
            )
            
            embed.add_field(
                name="🎯 Potential Reward",
                value="**15 points** (if approved)",
                inline=True
            )
            
            embed.add_field(
                name="📋 Next Steps",
                value="An admin will review your submission and award points if approved. You'll be notified of the decision!",
                inline=False
            )
            
            embed.set_footer(text="Thank you for participating in our events!")
            
            # Set the attached image as embed image
            embed.set_image(url=attachment.url)
            
            await ctx.send(embed=embed)
            
            # Forward to admin channel for review (with image URL)
            await self.forward_to_admin_channel(ctx, "Event", description, attachment.url, submission_id)
            
        except Exception as e:
            await ctx.send("❌ An error occurred while submitting your event attendance.")
            print(f"Error in event command: {e}")

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)  # 1 use per 10 seconds per user
    async def resource(self, ctx, *, args: str = ""):
        """Submit a resource for admin review and potential points
        
        Usage: !resource <description>
        Example: !resource "Found this amazing Python tutorial that covers web scraping basics"
        """
        try:
            # Parse the arguments
            description = args.strip()
            
            # Check if user provided a description
            if not description:
                embed = discord.Embed(
                    title="❌ Missing Resource Description",
                    description="Please provide a description of the resource you want to share.",
                    color=0xff0000
                )
                embed.add_field(
                    name="📝 Usage",
                    value="`!resource <description>`",
                    inline=False
                )
                embed.add_field(
                    name="💡 Example",
                    value="`!resource \"Found this amazing Python tutorial that covers web scraping basics\"`",
                    inline=False
                )
                embed.add_field(
                    name="📋 What to Include",
                    value="• What the resource is (tutorial, tool, article, etc.)\n• What it teaches or provides\n• Why it's valuable to the community",
                    inline=False
                )
                await ctx.send(embed=embed)
                return
            
            # Check if description is too short
            if len(description) < 15:
                embed = discord.Embed(
                    title="❌ Description Too Short",
                    description="Please provide a more detailed description (at least 15 characters).",
                    color=0xff0000
                )
                embed.add_field(
                    name="📝 Current Description",
                    value=f"\"{description}\"",
                    inline=False
                )
                embed.add_field(
                    name="💡 Make it Better",
                    value="• Add what type of resource it is\n• Explain what it teaches or provides\n• Mention why it's useful",
                    inline=False
                )
                embed.add_field(
                    name="📋 Example",
                    value="`!resource \"Found this comprehensive Python tutorial that teaches web scraping with beautiful soup and requests libraries\"`",
                    inline=False
                )
                await ctx.send(embed=embed)
                return
            
            # Submit resource to backend
            success, submission_id = await self.submit_resource_to_backend(str(ctx.author.id), description)
            
            if not success:
                await ctx.send("❌ Failed to submit resource to backend. Please try again later.")
                return
            
            # Create submission confirmation embed
            embed = discord.Embed(
                title="📚 Resource Submission Received",
                description=f"{ctx.author.mention}, your resource has been submitted for admin review!",
                color=0x0099ff
            )
            
            embed.add_field(
                name="📝 Resource Description",
                value=f"**{description[:200]}{'...' if len(description) > 200 else ''}**",
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
            
            # Forward to admin channel for review
            await self.forward_to_admin_channel(ctx, "Resource", description, "", submission_id)
            
        except Exception as e:
            await ctx.send("❌ An error occurred while processing your resource share.")
            print(f"Error in resource command: {e}")

    async def find_admin_channel(self, guild):
        """Find the admin channel in the guild"""
        try:
            # Look for a channel named "admin"
            for channel in guild.text_channels:
                if channel.name.lower() == "admin":
                    # Check if bot has permission to send messages
                    if channel.permissions_for(guild.me).send_messages:
                        print(f"Found admin channel: #{channel.name}")
                        return channel
            
            print("No 'admin' channel found")
            return None
            
        except Exception as e:
            print(f"Error finding admin channel: {e}")
            return None

    async def forward_to_admin_channel(self, ctx, submission_type, description="", additional_info="", submission_id=None):
        """Forward user submissions to admin channel for review with interactive buttons"""
        try:
            import os
            admin_channel_id = os.getenv('ADMIN_CHANNEL_ID')
            admin_channel = None
            
            # Try to get admin channel from environment variable first
            if admin_channel_id and admin_channel_id != 'PLACEHOLDER_CHANNEL_ID':
                admin_channel = self.bot.get_channel(int(admin_channel_id))
            
            # If no admin channel found, try to find one automatically
            if not admin_channel:
                admin_channel = await self.find_admin_channel(ctx.guild)
            
            # If still no admin channel, fallback to DMing admins
            if not admin_channel:
                print("No admin channel found, falling back to DMing admins")
                await self.notify_admins_via_dm(ctx, submission_type, description, additional_info)
                return
            
            # Create admin notification embed
            embed = discord.Embed(
                title=f"🔔 New {submission_type} Submission",
                description=f"**{ctx.author.display_name}** has submitted a {submission_type.lower()} for review:",
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
            
            if submission_id:
                embed.add_field(
                    name="🆔 Submission ID",
                    value=f"**{submission_id}**",
                    inline=True
                )
            
            if description:
                embed.add_field(
                    name="📝 User Shared:",
                    value=f"**{description[:1000]}{'...' if len(description) > 1000 else ''}**",
                    inline=False
                )
            
            if additional_info:
                embed.add_field(
                    name="ℹ️ Additional Info",
                    value=additional_info,
                    inline=False
                )
            
            # For events, set the image if additional_info is an image URL
            if submission_type.lower() == "event" and additional_info and additional_info.startswith("http"):
                embed.set_image(url=additional_info)
            
            embed.set_footer(text=f"Channel: #{ctx.channel.name} | Server: {ctx.guild.name}")
            
            # Create interactive buttons
            class AdminActionView(discord.ui.View):
                def __init__(self, submission_type, submission_id, user_id, description, bot_instance):
                    super().__init__(timeout=86400)  # 24 hours timeout
                    self.submission_type = submission_type
                    self.submission_id = submission_id
                    self.user_id = user_id
                    self.description = description
                    self.bot_instance = bot_instance
                
                @discord.ui.button(label="Approve", style=discord.ButtonStyle.green, emoji="✅")
                async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if not interaction.user.guild_permissions.administrator:
                        await interaction.response.send_message("❌ You need administrator permissions to approve submissions.", ephemeral=True)
                        return
                    
                    # Show modal for approval details
                    modal = ApprovalModal(self.submission_type, self.submission_id, self.user_id, self.description, self.bot_instance, "approve")
                    await interaction.response.send_modal(modal)
                
                @discord.ui.button(label="Reject", style=discord.ButtonStyle.red, emoji="❌")
                async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if not interaction.user.guild_permissions.administrator:
                        await interaction.response.send_message("❌ You need administrator permissions to reject submissions.", ephemeral=True)
                        return
                    
                    # Show modal for rejection details
                    modal = RejectionModal(self.submission_type, self.submission_id, self.user_id, self.description, self.bot_instance)
                    await interaction.response.send_modal(modal)
                
            
            # Create the view with buttons
            view = AdminActionView(submission_type, submission_id, str(ctx.author.id), description, self)
            
            # Send to admin channel with buttons
            await admin_channel.send(embed=embed, view=view)
            
            print(f"✅ Forwarded {submission_type} submission to admin channel with interactive buttons")
            
        except Exception as e:
            print(f"Error forwarding to admin channel: {e}")
            # Fallback to DMing admins
            await self.notify_admins_via_dm(ctx, submission_type, description, additional_info)

    async def notify_admins_via_dm(self, ctx, submission_type, description="", additional_info=""):
        """Fallback method to notify admins via DM"""
        try:
            # Get all admins in the server
            admins = [member for member in ctx.guild.members if member.guild_permissions.administrator]
            
            if not admins:
                return
            
            # Create admin notification embed
            embed = discord.Embed(
                title=f"🔔 New {submission_type} Submission",
                description=f"**{ctx.author.display_name}** has submitted a {submission_type.lower()} for review:",
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
            
            if description:
                embed.add_field(
                    name="📝 Description",
                    value=description[:1000] + "..." if len(description) > 1000 else description,
                    inline=False
                )
            
            if additional_info:
                embed.add_field(
                    name="ℹ️ Additional Info",
                    value=additional_info,
                    inline=False
                )
            
            embed.add_field(
                name="🔧 Admin Actions",
                value=f"Use `!approve{submission_type.lower()}` or `!reject{submission_type.lower()}` commands to review this submission.",
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
    async def linkedin(self, ctx, *, args: str = ""):
        """Submit LinkedIn update for admin review and potential points
        
        Usage: !linkedin <linkedin_url> <description>
        Example: !linkedin https://linkedin.com/posts/... "Liked and commented on P2E's latest post about career tips"
        """
        try:
            # Parse the arguments
            parts = args.strip().split(' ', 1) if args.strip() else []
            
            # Check if LinkedIn URL is provided
            if not parts or len(parts) < 1:
                embed = discord.Embed(
                    title="❌ Missing LinkedIn URL",
                    description="Please provide a LinkedIn URL and description of what you shared.",
                    color=0xff0000
                )
                embed.add_field(
                    name="📝 Usage",
                    value="`!linkedin <linkedin_url> <description>`",
                    inline=False
                )
                embed.add_field(
                    name="💡 Examples",
                    value="• `!linkedin https://linkedin.com/posts/... \"Liked and commented on P2E's post\"`\n"
                          "• `!linkedin https://linkedin.com/posts/... \"Reposted P2E's career advice\"`\n"
                          "• `!linkedin https://linkedin.com/posts/... \"Shared original P2E content\"`",
                    inline=False
                )
                await ctx.send(embed=embed)
                return
            
            linkedin_url = parts[0].strip()
            
            # Validate LinkedIn URL
            if not self.is_valid_linkedin_url(linkedin_url):
                embed = discord.Embed(
                    title="❌ Invalid LinkedIn URL",
                    description="Please provide a valid LinkedIn URL.",
                    color=0xff0000
                )
                embed.add_field(
                    name="✅ Valid LinkedIn URLs",
                    value="• `https://linkedin.com/posts/...`\n"
                          "• `https://www.linkedin.com/posts/...`\n"
                          "• `https://linkedin.com/in/username`\n"
                          "• `https://www.linkedin.com/in/username`",
                    inline=False
                )
                embed.add_field(
                    name="💡 Your input",
                    value=f"`{linkedin_url}`",
                    inline=False
                )
                await ctx.send(embed=embed)
                return
            
            # Check if description is provided
            if len(parts) < 2 or not parts[1].strip():
                embed = discord.Embed(
                    title="❌ Missing Description",
                    description="Please describe what you shared on LinkedIn.",
                    color=0xff0000
                )
                embed.add_field(
                    name="📝 Usage",
                    value="`!linkedin <linkedin_url> <description>`",
                    inline=False
                )
                embed.add_field(
                    name="💡 Examples of descriptions",
                    value="• \"Liked and commented on P2E's latest post about career tips\"\n"
                          "• \"Reposted P2E's article about professional networking\"\n"
                          "• \"Shared original P2E content about resume building\"\n"
                          "• \"Engaged with P2E's discussion about interview preparation\"",
                    inline=False
                )
                await ctx.send(embed=embed)
                return
            
            description = parts[1].strip()
            
            # Validate description length
            if len(description) < 10:
                embed = discord.Embed(
                    title="❌ Description Too Short",
                    description="Please provide a more detailed description (at least 10 characters).",
                    color=0xff0000
                )
                embed.add_field(
                    name="💡 Good descriptions include:",
                    value="• What type of content you shared (like, comment, repost, original)\n"
                          "• The topic or theme of the content\n"
                          "• How you engaged with P2E content",
                    inline=False
                )
                embed.add_field(
                    name="📝 Your description",
                    value=f"`{description}` ({len(description)} characters)",
                    inline=False
                )
                await ctx.send(embed=embed)
                return
            
            # Combine URL and description for backend submission
            full_description = f"LinkedIn URL: {linkedin_url}\nDescription: {description}"
            
            # Submit LinkedIn to backend
            success, submission_id = await self.submit_linkedin_to_backend(str(ctx.author.id), full_description)
            
            if not success:
                await ctx.send("❌ Failed to submit LinkedIn update to backend. Please try again later.")
                return
            
            # Create submission confirmation embed
            embed = discord.Embed(
                title="💼 LinkedIn Update Submitted",
                description=f"{ctx.author.mention}, your LinkedIn update has been submitted for admin review!",
                color=0x0099ff
            )
            
            embed.add_field(
                name="🔗 LinkedIn URL",
                value=f"**[View Post]({linkedin_url})**",
                inline=False
            )
            
            embed.add_field(
                name="📝 User Shared:",
                value=f"**{description[:200]}{'...' if len(description) > 200 else ''}**",
                inline=False
            )
            
            embed.add_field(
                name="⏳ Status",
                value="🔄 **Pending Review**",
                inline=True
            )
            
            embed.add_field(
                name="🎯 Potential Reward",
                value="**5 points** (if approved)",
                inline=True
            )
            
            embed.add_field(
                name="📋 Next Steps",
                value="An admin will review your submission and award points if approved. You'll be notified of the decision!",
                inline=False
            )
            
            embed.set_footer(text="Thank you for sharing your professional updates!")
            
            await ctx.send(embed=embed)
            
            # Forward to admin channel for review
            await self.forward_to_admin_channel(ctx, "LinkedIn", full_description, "", submission_id)
            
        except Exception as e:
            await ctx.send("❌ An error occurred while submitting your LinkedIn update.")
            print(f"Error in linkedin command: {e}")
    
    def is_valid_linkedin_url(self, url):
        """Validate if the provided URL is a valid LinkedIn URL"""
        import re
        
        # LinkedIn URL patterns
        linkedin_patterns = [
            r'^https?://(www\.)?linkedin\.com/posts/.*',
            r'^https?://(www\.)?linkedin\.com/in/.*',
            r'^https?://(www\.)?linkedin\.com/feed/update/.*',
            r'^https?://(www\.)?linkedin\.com/pulse/.*',
            r'^https?://(www\.)?linkedin\.com/company/.*/posts/.*'
        ]
        
        for pattern in linkedin_patterns:
            if re.match(pattern, url, re.IGNORECASE):
                return True
        
        return False

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
        embed = discord.Embed(
            title="🚧 Feature in Development",
            description="The milestones feature is currently being developed and will be available soon!",
            color=0xffaa00
        )
        embed.add_field(
            name="What's Coming",
            value="• View your progress towards incentives\n• Track milestone achievements\n• See available rewards",
            inline=False
        )
        embed.add_field(
            name="Stay Tuned",
            value="We're working hard to bring you an amazing milestone tracking experience!",
            inline=False
        )
        await ctx.send(embed=embed)

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
    async def approveresource(self, ctx, submission_id: int, points: int, *, notes: str = ""):
        """Approve a resource submission and award points"""
        try:
            success, result = await self.approve_resource_backend(submission_id, points, notes)
            
            if not success:
                await ctx.send(f"❌ Failed to approve resource: {result}")
                return
            
            # Create approval embed
            embed = discord.Embed(
                title="✅ Resource Approved!",
                description=f"Resource submission has been approved and points awarded!",
                color=0x00ff00
            )
            
            embed.add_field(
                name="📝 Submission ID",
                value=f"**{submission_id}**",
                inline=True
            )
            
            embed.add_field(
                name="🎯 Points Awarded",
                value=f"**{points} points**",
                inline=True
            )
            
            embed.add_field(
                name="📊 New Total",
                value=f"**{result.get('total_points', 'N/A')} points**",
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
            await self.notify_user_of_approval(result.get('user_id'), points, notes)
            
        except Exception as e:
            await ctx.send(f"❌ Error approving resource: {e}")
            print(f"Error in approveresource command: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def rejectresource(self, ctx, submission_id: int, *, reason: str = "No reason provided"):
        """Reject a resource submission"""
        try:
            success, result = await self.reject_resource_backend(submission_id, reason)
            
            if not success:
                await ctx.send(f"❌ Failed to reject resource: {result}")
                return
            
            # Create rejection embed
            embed = discord.Embed(
                title="❌ Resource Rejected",
                description=f"Resource submission has been rejected.",
                color=0xff0000
            )
            
            embed.add_field(
                name="📝 Submission ID",
                value=f"**{submission_id}**",
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
            await self.notify_user_of_rejection(result.get('user_id'), reason)
            
        except Exception as e:
            await ctx.send(f"❌ Error rejecting resource: {e}")
            print(f"Error in rejectresource command: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def pendingresources(self, ctx):
        """Show all pending resource submissions"""
        try:
            # Fetch pending resources from backend
            response = await self._backend_request({
                "action": "pending-resources"
            })
            
            if not response:
                await ctx.send("❌ Failed to fetch pending resources from backend.")
                return
            
            submissions = response.get("submissions", [])
            pending_count = response.get("pending_count", 0)
            
            if not submissions or pending_count == 0:
                await ctx.send("✅ No pending resource submissions!")
                return
            
            embed = discord.Embed(
                title="📚 Pending Resource Submissions",
                description=f"Found **{pending_count}** pending submission(s):",
                color=0xff9900
            )
            
            for i, submission in enumerate(submissions[:10], 1):
                # Format the submission date
                from datetime import datetime
                submitted_at = datetime.fromisoformat(submission['submitted_at'].replace('Z', '+00:00'))
                timestamp = int(submitted_at.timestamp())
                
                embed.add_field(
                    name=f"#{i} - <@{submission['discord_id']}>",
                    value=f"**User:** {submission['username']}\n**Submitted:** <t:{timestamp}:R>\n**Description:** {submission['description'][:200]}{'...' if len(submission['description']) > 200 else ''}\n**ID:** {submission['id']}",
                    inline=False
                )
            
            # Add spacing field for visual separation
            embed.add_field(
                name="\u200b",  # Zero-width space for spacing
                value="\u200b",  # Zero-width space for spacing
                inline=False
            )
            
            # Move "And X more submissions..." above admin instructions
            if len(submissions) > 10:
                embed.add_field(
                    name="📊 Additional Submissions",
                    value=f"**And {len(submissions) - 10} more submissions...**",
                    inline=False
                )
            
            embed.add_field(
                name="⚡ **ADMIN ACTIONS**",
                value="**To approve a resource:**\n`!approveresource <submission_id> <points> [notes]`\n\n**To reject a resource:**\n`!rejectresource <submission_id> [reason]`\n\n**Example:**\n`!approveresource 25 10 Great resource!`\n`!rejectresource 26 Not relevant to our community`",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error fetching pending resources: {e}")
            print(f"Error in pendingresources command: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def pendingevents(self, ctx):
        """Show all pending event submissions - OPTIMIZED"""
        try:
            # Fetch pending events from backend
            response = await self._backend_request({
                "action": "pending-events"
            })
            
            if not response:
                await ctx.send("❌ Failed to fetch pending events from backend.")
                return
            
            submissions = response.get("submissions", [])
            pending_count = response.get("pending_count", 0)
            
            if not submissions or pending_count == 0:
                await ctx.send("✅ No pending event submissions!")
                return
            
            embed = discord.Embed(
                title="🎪 Pending Event Submissions",
                description=f"Found **{pending_count}** pending submission(s):",
                color=0xff9900
            )
            
            for i, submission in enumerate(submissions[:10], 1):
                # Format the submission date
                from datetime import datetime
                submitted_at = datetime.fromisoformat(submission['submitted_at'].replace('Z', '+00:00'))
                timestamp = int(submitted_at.timestamp())
                
                embed.add_field(
                    name=f"#{i} - <@{submission['discord_id']}>",
                    value=f"**User:** {submission['username']}\n**Event:** {submission['event_name']}\n**Submitted:** <t:{timestamp}:R>\n**Description:** {submission['description'][:200]}{'...' if len(submission['description']) > 200 else ''}\n**ID:** {submission['id']}",
                    inline=False
                )
            
            if len(submissions) > 10:
                embed.add_field(
                    name="📊 Additional Submissions",
                    value=f"**And {len(submissions) - 10} more submissions...**",
                    inline=False
                )
            
            embed.add_field(
                name="⚡ **ADMIN ACTIONS**",
                value="**To approve an event:**\n`!approveevent <submission_id> <points> [notes]`\n\n**To reject an event:**\n`!rejectevent <submission_id> [reason]`\n\n**Example:**\n`!approveevent 25 15 Great attendance!`\n`!rejectevent 26 Event not verified`",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error fetching pending events: {e}")
            print(f"Error in pendingevents command: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def pendinglinkedin(self, ctx):
        """Show all pending LinkedIn submissions - OPTIMIZED"""
        try:
            # Fetch pending LinkedIn from backend
            response = await self._backend_request({
                "action": "pending-linkedin"
            })
            
            if not response:
                await ctx.send("❌ Failed to fetch pending LinkedIn submissions from backend.")
                return
            
            submissions = response.get("submissions", [])
            pending_count = response.get("pending_count", 0)
            
            if not submissions or pending_count == 0:
                await ctx.send("✅ No pending LinkedIn submissions!")
                return
            
            embed = discord.Embed(
                title="💼 Pending LinkedIn Submissions",
                description=f"Found **{pending_count}** pending submission(s):",
                color=0xff9900
            )
            
            for i, submission in enumerate(submissions[:10], 1):
                # Format the submission date
                from datetime import datetime
                submitted_at = datetime.fromisoformat(submission['submitted_at'].replace('Z', '+00:00'))
                timestamp = int(submitted_at.timestamp())
                
                embed.add_field(
                    name=f"#{i} - <@{submission['discord_id']}>",
                    value=f"**User:** {submission['username']}\n**Submitted:** <t:{timestamp}:R>\n**Description:** {submission['description'][:200]}{'...' if len(submission['description']) > 200 else ''}\n**ID:** {submission['id']}",
                    inline=False
                )
            
            if len(submissions) > 10:
                embed.add_field(
                    name="📊 Additional Submissions",
                    value=f"**And {len(submissions) - 10} more submissions...**",
                    inline=False
                )
            
            embed.add_field(
                name="⚡ **ADMIN ACTIONS**",
                value="**To approve LinkedIn update:**\n`!approvelinkedin <submission_id> <points> [notes]`\n\n**To reject LinkedIn update:**\n`!rejectlinkedin <submission_id> [reason]`\n\n**Example:**\n`!approvelinkedin 25 5 Great update!`\n`!rejectlinkedin 26 Not professional enough`",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error fetching pending LinkedIn submissions: {e}")
            print(f"Error in pendinglinkedin command: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def adminreport(self, ctx):
        """Manually trigger an admin report with pending submission counts"""
        try:
            await self.send_hourly_admin_report()
            await ctx.send("✅ Admin report sent!")
        except Exception as e:
            await ctx.send(f"❌ Error sending admin report: {e}")
            print(f"Error in adminreport command: {e}")

    async def send_hourly_admin_report(self):
        """Send hourly admin report with pending submission counts (8 AM - 8 PM EST)"""
        try:
            # Check if it's within business hours (8 AM - 8 PM EST)
            import pytz
            from datetime import datetime
            
            est = pytz.timezone('US/Eastern')
            now_est = datetime.now(est)
            current_hour = now_est.hour
            
            # Only send reports between 8 AM and 8 PM EST
            if current_hour < 8 or current_hour >= 20:
                return
            
            # Get pending counts from backend
            pending_counts = {}
            
            # Get pending resources count
            try:
                response = await self._backend_request({"action": "pending-resources"})
                if response:
                    pending_counts['resources'] = response.get("pending_count", 0)
                else:
                    pending_counts['resources'] = 0
            except Exception:
                pending_counts['resources'] = 0
            
            # Get pending events count
            try:
                response = await self._backend_request({"action": "pending-events"})
                if response:
                    pending_counts['events'] = response.get("pending_count", 0)
                else:
                    pending_counts['events'] = 0
            except Exception:
                pending_counts['events'] = 0
            
            # Get pending LinkedIn count
            try:
                response = await self._backend_request({"action": "pending-linkedin"})
                if response:
                    pending_counts['linkedin'] = response.get("pending_count", 0)
                else:
                    pending_counts['linkedin'] = 0
            except Exception:
                pending_counts['linkedin'] = 0
            
            # Calculate total pending
            total_pending = pending_counts['resources'] + pending_counts['events'] + pending_counts['linkedin']
            
            # Create embed
            embed = discord.Embed(
                title="📊 Hourly Admin Report",
                description=f"Pending submissions as of {now_est.strftime('%I:%M %p EST')}",
                color=0x0099ff if total_pending == 0 else (0xff9900 if total_pending < 10 else 0xff0000)
            )
            
            # Add submission counts
            embed.add_field(
                name="📝 Pending Resources",
                value=f"**{pending_counts['resources']}** submissions",
                inline=True
            )
            
            embed.add_field(
                name="🎪 Pending Events",
                value=f"**{pending_counts['events']}** submissions",
                inline=True
            )
            
            embed.add_field(
                name="💼 Pending LinkedIn",
                value=f"**{pending_counts['linkedin']}** submissions",
                inline=True
            )
            
            embed.add_field(
                name="📊 Total Pending",
                value=f"**{total_pending}** submissions",
                inline=True
            )
            
            # Add status indicator
            if total_pending == 0:
                embed.add_field(
                    name="✅ Status",
                    value="All caught up! No pending submissions.",
                    inline=True
                )
            elif total_pending < 10:
                embed.add_field(
                    name="⚠️ Status",
                    value="Some submissions pending review.",
                    inline=True
                )
            else:
                embed.add_field(
                    name="🚨 Status",
                    value="High volume of pending submissions!",
                    inline=True
                )
            
            # Add quick action commands
            embed.add_field(
                name="🔧 Quick Actions",
                value="`!pendingresources` - View pending resources\n`!pendingevents` - View pending events\n`!pendinglinkedin` - View pending LinkedIn",
                inline=False
            )
            
            embed.set_footer(text="Automated hourly report • Next report in 1 hour")
            
            # Send to admin channel
            await self.send_to_admin_channel(embed)
            
        except Exception as e:
            print(f"Error sending hourly admin report: {e}")

    async def send_to_admin_channel(self, embed):
        """Send embed to admin channel"""
        try:
            # Find admin channel (you may need to adjust this based on your server setup)
            admin_channel = None
            
            # Try to find a channel named 'admin', 'moderator', 'staff', or 'general'
            for channel in self.bot.get_all_channels():
                if isinstance(channel, discord.TextChannel):
                    channel_name_lower = channel.name.lower()
                    if any(keyword in channel_name_lower for keyword in ['admin', 'moderator', 'staff', 'general']):
                        admin_channel = channel
                        break
            
            if admin_channel:
                await admin_channel.send(embed=embed)
            else:
                print("No admin channel found for hourly report")
                
        except Exception as e:
            print(f"Error sending to admin channel: {e}")

    async def start_hourly_reports(self):
        """Start the hourly reporting task"""
        import asyncio
        
        while True:
            try:
                await self.send_hourly_admin_report()
                # Wait 1 hour (3600 seconds)
                await asyncio.sleep(3600)
            except Exception as e:
                print(f"Error in hourly reports loop: {e}")
                # Wait 5 minutes before retrying
                await asyncio.sleep(300)

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

    @commands.command()
    async def streak(self, ctx):
        """Track engagement streaks (daily/weekly)"""
        try:
            user_id = str(ctx.author.id)
            
            # Fetch streak data from backend
            response = await self._backend_request({
                "action": "get-streak",
                "discord_id": user_id
            })
            
            if not response:
                await ctx.send("❌ Failed to fetch streak data from backend.")
                return
            
            current_streak = response.get('current_streak', 0)
            longest_streak = response.get('longest_streak', 0)
            streak_type = response.get('streak_type', 'daily')
            last_activity = response.get('last_activity', 'Never')
            streak_bonus = response.get('streak_bonus', 0)
            
            embed = discord.Embed(
                title="🔥 Engagement Streak",
                description=f"Your current {streak_type} engagement streak",
                color=0xff6b35 if current_streak > 0 else 0x666666
            )
            
            embed.add_field(
                name="Current Streak",
                value=f"**{current_streak}** {streak_type} streak(s)",
                inline=True
            )
            
            embed.add_field(
                name="Longest Streak",
                value=f"**{longest_streak}** {streak_type} streak(s)",
                inline=True
            )
            
            embed.add_field(
                name="Streak Bonus",
                value=f"**+{streak_bonus}** points",
                inline=True
            )
            
            embed.add_field(
                name="Last Activity",
                value=last_activity,
                inline=False
            )
            
            if current_streak >= 7:
                embed.add_field(
                    name="🎉 Streak Milestone!",
                    value="You're on fire! Keep it up!",
                    inline=False
                )
            elif current_streak >= 3:
                embed.add_field(
                    name="💪 Great Progress!",
                    value="You're building a solid streak!",
                    inline=False
                )
            else:
                embed.add_field(
                    name="💡 Streak Tips",
                    value="• Send messages daily to maintain your streak\n• React to posts to boost engagement\n• Participate in events and activities",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send("❌ An error occurred while fetching streak data.")
            print(f"Error in streak command: {e}")

    @commands.command()
    async def levelup(self, ctx):
        """Show progress toward the next tier or badge"""
        embed = discord.Embed(
            title="🚧 Coming Soon!",
            description="The level system is not yet implemented but is coming soon!",
            color=0xffaa00
        )
        embed.add_field(
            name="What's Coming",
            value="• Level progression system\n• Tier-based benefits\n• Visual progress tracking\n• Achievement badges",
            inline=False
        )
        embed.add_field(
            name="Stay Tuned",
            value="We're working hard to bring you an amazing leveling experience!",
            inline=False
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def badge(self, ctx):
        """Display earned career/professional badges"""
        embed = discord.Embed(
            title="🏆 Coming Soon!",
            description="The badge system is not yet implemented but is coming soon!",
            color=0xffaa00
        )
        embed.add_field(
            name="What's Coming",
            value="• Career achievement badges\n• Professional milestone badges\n• Activity completion badges\n• Special recognition badges",
            inline=False
        )
        embed.add_field(
            name="Stay Tuned",
            value="We're working hard to bring you an amazing badge collection system!",
            inline=False
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def leaderboard(self, ctx, category: str = "total"):
        """Show leaderboard by category (networking, learning, event attendance)"""
        try:
            # Validate category
            valid_categories = ["total", "networking", "learning", "events", "resume_reviews", "resources"]
            if category.lower() not in valid_categories:
                await ctx.send(f"❌ Invalid category. Available categories: {', '.join(valid_categories)}")
                return
            
            category = category.lower()
            
            # Fetch leaderboard data from backend
            response = await self._backend_request({
                "action": "leaderboard-category",
                "category": category,
                "limit": 10
            })
            
            leaderboard_data = response.get('leaderboard', [])
            category_name = response.get('category_name', category.title())
            total_users = response.get('total_users', 0)
            
            embed = discord.Embed(
                title=f"🏆 {category_name} Leaderboard",
                description=f"Top performers in {category_name.lower()}",
                color=0x00ff88
            )
            
            if not leaderboard_data:
                embed.add_field(
                    name="📊 No Data",
                    value="No data available for this category yet.",
                    inline=False
                )
            else:
                for i, user_data in enumerate(leaderboard_data, 1):
                    user_id = user_data.get('discord_id')
                    points = user_data.get('points', 0)
                    username = user_data.get('username', f'User {user_id}')
                    
                    # Get Discord user if possible
                    try:
                        user = await self.bot.fetch_user(int(user_id))
                        display_name = user.display_name
                    except:
                        display_name = username
                    
                    # Medal emojis for top 3
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**#{i}**"
                    
                    embed.add_field(
                        name=f"{medal} {display_name}",
                        value=f"**{points:,}** {category_name.lower()} points",
                        inline=True
                    )
            
            embed.add_field(
                name="📈 Total Users",
                value=f"**{total_users}** users tracked",
                inline=True
            )
            
            embed.add_field(
                name="💡 Categories",
                value="Use `!leaderboard <category>` for:\n• networking\n• learning\n• events\n• resume_reviews\n• resources",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send("❌ An error occurred while fetching leaderboard data.")
            print(f"Error in leaderboard command: {e}")

async def setup(bot):
    await bot.add_cog(Points(bot))
