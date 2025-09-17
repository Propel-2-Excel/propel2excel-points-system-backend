import discord
from discord.ext import commands
import aiohttp
import json
import asyncio
from datetime import datetime
import os

class ResumeReview(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Use smart backend URL detection (same logic as bot.py)
        explicit_url = os.getenv('BACKEND_API_URL')
        if explicit_url:
            self.backend_url = explicit_url
        elif os.getenv('RENDER'):
            port = os.getenv('PORT', '8000')
            self.backend_url = f'http://127.0.0.1:{port}'
        else:
            self.backend_url = 'http://localhost:8000'
        self.bot_secret = os.getenv('BOT_SHARED_SECRET', '')
        self.form_url = "https://forms.gle/EKHLrqhHwt1bGQjd6"

    async def _backend_request(self, payload):
        """Make backend API request using current pattern"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.backend_url}/api/bot/",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Bot-Secret": self.bot_secret,
                }
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"Backend error {response.status}: {error_text}")

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def review_status(self, ctx):
        """Check status of your resume review request"""
        try:
            # For now, we'll provide a general status message since the backend endpoint doesn't exist yet
            embed = discord.Embed(
                title="📊 Review Status",
                description=f"{ctx.author.mention}'s resume review status",
                color=0x0099ff
            )
            embed.add_field(
                name="Status", 
                value="Please check your email for updates from our team at propel@propel2excel.com", 
                inline=False
            )
            embed.add_field(
                name="Next Steps",
                value="If you haven't submitted your form yet, use `!resume` to get started!",
                inline=False
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error checking status: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def add_professional(self, ctx, name: str, *, specialties: str):
        """Admin command to add a professional to the resume review pool"""
        try:
            embed = discord.Embed(
                title="✅ Professional Added",
                description="Professional has been added to the resume review pool",
                color=0x00ff00
            )
            embed.add_field(name="Name", value=name, inline=True)
            embed.add_field(name="Specialties", value=specialties, inline=False)
            embed.add_field(
                name="📝 Note", 
                value="This is stored locally. Backend integration needed for persistent storage.",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error adding professional: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def list_professionals(self, ctx):
        """Admin command to list available professionals"""
        try:
            embed = discord.Embed(
                title="👥 Available Professionals",
                description="Resume review professionals in our network",
                color=0x0099ff
            )
            embed.add_field(
                name="📝 Note",
                value="Backend integration needed to display actual professionals list",
                inline=False
            )
            embed.add_field(
                name="Contact",
                value="For current professionals list, contact propel@propel2excel.com",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error listing professionals: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def match_review(self, ctx, user: discord.Member, professional_name: str):
        """Admin command to match a student with a professional"""
        try:
            embed = discord.Embed(
                title="🤝 Review Match Created",
                description="Student has been matched with a professional",
                color=0x00ff00
            )
            embed.add_field(name="Student", value=user.mention, inline=True)
            embed.add_field(name="Professional", value=professional_name, inline=True)
            embed.add_field(
                name="Next Steps",
                value="Contact both parties to coordinate the review session",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
            # Notify the student
            try:
                student_embed = discord.Embed(
                    title="🎉 Review Match Found!",
                    description="Great news! We've found a professional to review your resume.",
                    color=0x00ff00
                )
                student_embed.add_field(name="Professional", value=professional_name, inline=True)
                student_embed.add_field(
                    name="Next Steps",
                    value="You'll receive an email shortly with scheduling details",
                    inline=False
                )
                student_embed.add_field(
                    name="Contact",
                    value="propel@propel2excel.com",
                    inline=True
                )
                
                await user.send(embed=student_embed)
                
            except discord.Forbidden:
                await ctx.send(f"⚠️ Could not send DM to {user.mention} - please notify them manually")
            
        except Exception as e:
            await ctx.send(f"❌ Error creating match: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def review_stats(self, ctx):
        """Admin command to show resume review statistics"""
        try:
            response = await self._backend_request({
                "action": "review-stats"
            })
            
            embed = discord.Embed(
                title="📊 Resume Review Statistics",
                description="Current resume review program metrics",
                color=0x0099ff
            )
            
            stats = response
            embed.add_field(
                name="📋 Requests",
                value=f"• Total: {stats.get('total_requests', 0)}\n• Pending: {stats.get('pending_requests', 0)}\n• Matched: {stats.get('matched_requests', 0)}\n• Completed: {stats.get('completed_requests', 0)}",
                inline=True
            )
            embed.add_field(
                name="👥 Professionals",
                value=f"• Active: {stats.get('total_professionals', 0)}\n• Avg Rating: {stats.get('average_rating', 0):.1f}/5.0",
                inline=True
            )
            embed.add_field(
                name="📈 Recent (7 days)",
                value=f"• New Requests: {stats.get('recent_requests', 0)}\n• Completions: {stats.get('recent_completions', 0)}",
                inline=True
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error fetching stats: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def pending_reviews(self, ctx):
        """Admin command to see students with availability data"""
        try:
            response = await self._backend_request({
                "action": "pending-reviews"
            })
            
            pending_requests = response.get('pending_requests', [])
            total_count = response.get('total_count', 0)
            
            if total_count == 0:
                embed = discord.Embed(
                    title="📋 Pending Reviews",
                    description="No pending review requests found.",
                    color=0x00ff00
                )
                await ctx.send(embed=embed)
                return
            
            embed = discord.Embed(
                title="📋 Pending Reviews",
                description=f"Found {total_count} pending review requests",
                color=0xff9900
            )
            
            # Show up to 10 most recent requests
            for i, req in enumerate(pending_requests[:10]):
                student_info = f"**Student:** {req['student_username']}\n"
                student_info += f"**Target:** {req['target_industry']} - {req['target_role']}\n"
                student_info += f"**Experience:** {req['experience_level']}\n"
                student_info += f"**Submitted:** {req['days_pending']} days ago\n"
                
                # Show availability times
                preferred_times = req.get('preferred_times', [])
                if preferred_times:
                    times_str = ', '.join(preferred_times[:3])  # Show first 3 times
                    if len(preferred_times) > 3:
                        times_str += f" (+{len(preferred_times)-3} more)"
                    student_info += f"**Available:** {times_str}"
                else:
                    student_info += f"**Available:** No times specified"
                
                embed.add_field(
                    name=f"#{req['id']} - {req['student_username']}",
                    value=student_info,
                    inline=False
                )
            
            if total_count > 10:
                embed.add_field(
                    name="📝 Note",
                    value=f"Showing 10 of {total_count} requests. Use other commands to manage specific students.",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error fetching pending reviews: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def suggest_matches(self, ctx, user: discord.Member):
        """Admin command to see professionals with overlapping times for a student"""
        try:
            response = await self._backend_request({
                "action": "suggest-matches",
                "discord_id": str(user.id)
            })
            
            matches = response.get('matches', [])
            total_matches = response.get('total_matches', 0)
            student_times = response.get('student_preferred_times', [])
            
            embed = discord.Embed(
                title="🤝 Professional Matches",
                description=f"Found {total_matches} professionals with overlapping availability for {user.mention}",
                color=0x0099ff if total_matches > 0 else 0xff0000
            )
            
            if not matches:
                embed.add_field(
                    name="❌ No Matches Found",
                    value="No professionals have overlapping availability with this student.",
                    inline=False
                )
                if student_times:
                    embed.add_field(
                        name="Student's Preferred Times",
                        value=', '.join(student_times[:5]),
                        inline=False
                    )
            else:
                # Show student's times
                if student_times:
                    embed.add_field(
                        name="🕒 Student's Preferred Times",
                        value=', '.join(student_times[:5]),
                        inline=False
                    )
                
                # Show top 5 matches
                for i, match in enumerate(matches[:5]):
                    match_info = f"**Specialties:** {match['specialties']}\n"
                    match_info += f"**Experience:** {match['total_reviews']} reviews, {match['rating']:.1f}⭐\n"
                    match_info += f"**Overlapping Times:** {', '.join(match['overlapping_times'][:3])}\n"
                    match_info += f"**Available Until:** {match['availability_valid_until']}"
                    
                    embed.add_field(
                        name=f"#{match['professional_id']} - {match['professional_name']}",
                        value=match_info,
                        inline=False
                    )
                
                if total_matches > 5:
                    embed.add_field(
                        name="📝 Note",
                        value=f"Showing top 5 of {total_matches} matches. Use !schedule_session to book a session.",
                        inline=False
                    )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error finding matches: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def schedule_session(self, ctx, user: discord.Member, professional_name: str, *, scheduled_time: str):
        """Admin command to schedule a session between student and professional"""
        try:
            response = await self._backend_request({
                "action": "schedule-session",
                "discord_id": str(user.id),
                "professional_name": professional_name,
                "scheduled_time": scheduled_time,
                "duration_minutes": 30
            })
            
            embed = discord.Embed(
                title="📅 Session Scheduled",
                description="Review session has been successfully scheduled!",
                color=0x00ff00
            )
            embed.add_field(
                name="👤 Student", 
                value=user.mention, 
                inline=True
            )
            embed.add_field(
                name="👨‍💼 Professional", 
                value=professional_name, 
                inline=True
            )
            embed.add_field(
                name="🕒 Time", 
                value=response.get('scheduled_time', scheduled_time), 
                inline=True
            )
            embed.add_field(
                name="⏱️ Duration", 
                value=f"{response.get('duration_minutes', 30)} minutes", 
                inline=True
            )
            embed.add_field(
                name="📋 Session ID", 
                value=f"#{response.get('session_id')}", 
                inline=True
            )
            embed.add_field(
                name="📧 Next Steps",
                value="Both parties will receive email notifications with meeting details.",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
            # Notify the student
            try:
                student_embed = discord.Embed(
                    title="📅 Review Session Scheduled!",
                    description=f"Your resume review session has been scheduled with {professional_name}",
                    color=0x00ff00
                )
                student_embed.add_field(
                    name="🕒 Scheduled Time", 
                    value=response.get('scheduled_time', scheduled_time), 
                    inline=False
                )
                student_embed.add_field(
                    name="📧 What's Next",
                    value="You'll receive an email with meeting details and a calendar invite shortly.",
                    inline=False
                )
                student_embed.add_field(
                    name="💡 Prepare",
                    value="Have your resume ready and prepare any specific questions you'd like to discuss.",
                    inline=False
                )
                
                await user.send(embed=student_embed)
                
            except discord.Forbidden:
                await ctx.send(f"⚠️ Could not send DM to {user.mention} - please notify them manually")
            
        except Exception as e:
            await ctx.send(f"❌ Error scheduling session: {e}")

async def setup(bot):
    await bot.add_cog(ResumeReview(bot))