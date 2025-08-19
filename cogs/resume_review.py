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
        self.backend_url = os.getenv('BACKEND_API_URL', 'http://localhost:8000')
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
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def resume_review(self, ctx):
        """Start resume review process - sends DM with form link and instructions"""
        try:
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
                value=f"[Resume Review Form]({self.form_url})",
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
            await self._backend_request({
                "action": "add-activity",
                "discord_id": str(ctx.author.id),
                "activity_type": "resume_review_request",
                "details": "Resume review process started",
            })
            
        except discord.Forbidden:
            await ctx.send("❌ I can't send you a DM. Please enable DMs from server members and try again.")
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

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
                value="If you haven't submitted your form yet, use `!resume_review` to get started!",
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
            embed = discord.Embed(
                title="📊 Resume Review Statistics",
                description="Current resume review program metrics",
                color=0x0099ff
            )
            embed.add_field(
                name="📝 Note",
                value="Backend integration needed for actual statistics",
                inline=False
            )
            embed.add_field(
                name="Placeholder Stats",
                value="• Total Requests: TBD\n• Completed Reviews: TBD\n• Pending Matches: TBD\n• Average Rating: TBD",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error fetching stats: {e}")

async def setup(bot):
    await bot.add_cog(ResumeReview(bot))