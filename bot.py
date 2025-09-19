import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import logging
import sys
from datetime import datetime
import math
import json
import aiohttp

# Add current directory to Python path for cog imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

def get_backend_url():
    """Smart backend URL selection based on environment"""
    # Check if BACKEND_API_URL is explicitly set
    explicit_url = os.getenv('BACKEND_API_URL')
    if explicit_url:
        return explicit_url
    
    # For Render deployment, use localhost when bot and backend are in same container
    if os.getenv('RENDER'):
        port = os.getenv('PORT', '8000')
        return f'http://127.0.0.1:{port}'
    
    # Default to localhost for local development
    return 'http://localhost:8000'

BACKEND_API_URL = get_backend_url()
BOT_SHARED_SECRET = os.getenv('BOT_SHARED_SECRET', '')

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
bot.start_time = datetime.utcnow()

# Global variables
cogs_loaded = False
reconnect_attempts = 0
max_reconnect_attempts = 5

async def register_user_with_backend(discord_id: str, display_name: str, username: str = None):
    """Register a new user with the backend API when they join Discord"""
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "action": "upsert-user",
                "discord_id": discord_id,
                "display_name": display_name,
                "username": username,
            }
            
            async with session.post(
                f"{BACKEND_API_URL}/api/bot/",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Bot-Secret": BOT_SHARED_SECRET,
                }
            ) as response:
                if response.status in (200, 201):
                    logger.info(f"✅ Successfully registered user {display_name} ({discord_id}) with backend")
                    return True
                elif response.status == 409:
                    logger.info(f"ℹ️ User {display_name} ({discord_id}) already exists in backend")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Failed to register user {display_name} ({discord_id}) with backend: {response.status} - {error_text}")
                    return False
                    
    except Exception as e:
        logger.error(f"❌ Error registering user {display_name} ({discord_id}) with backend: {e}")
        return False

async def validate_discord_username(discord_username: str):
    """Validate if a Discord username exists in the current server"""
    try:
        if not discord_username:
            return {"valid": False, "message": "Discord username is required"}
        
        # Get the guild (server) - assumes bot is only in one server
        guild = None
        for g in bot.guilds:
            guild = g
            break
            
        if not guild:
            return {"valid": False, "message": "Bot is not connected to any Discord server"}
        
        # Search for the user by username (can include discriminator)
        username_parts = discord_username.split('#')
        base_username = username_parts[0]
        discriminator = username_parts[1] if len(username_parts) > 1 else None
        
        # Search through guild members for UNIQUE USERNAME match
        # Discord usernames are unique, so we only need to check the actual username
        
        for member in guild.members:
            # Check against unique Discord username (with optional discriminator)
            if member.name.lower() == base_username.lower():
                # If discriminator provided, verify it matches
                if discriminator is not None:
                    if member.discriminator == discriminator:
                        return {
                            "valid": True, 
                            "message": f"User found in {guild.name}", 
                            "discord_id": str(member.id),
                            "display_name": member.display_name,
                            "username": f"{member.name}#{member.discriminator}"
                        }
                else:
                    # No discriminator provided, username match is sufficient (usernames are unique)
                    return {
                        "valid": True, 
                        "message": f"User found in {guild.name}", 
                        "discord_id": str(member.id),
                        "display_name": member.display_name,
                        "username": f"{member.name}#{member.discriminator}"
                    }
        
        return {"valid": False, "message": f"User '{discord_username}' not found in {guild.name}"}
        
    except Exception as e:
        logger.error(f"Error validating Discord username '{discord_username}': {e}")
        return {"valid": False, "message": "Error validating Discord username"}

async def update_user_points_in_backend(discord_id: str, points: int, action: str):
    """Update user points in the backend API"""
    try:
        async with aiohttp.ClientSession() as session:
            # Map free-form actions to Activity.activity_type values
            action_map = {
                "Message sent": "discord_activity",
                "Liking/interacting": "like_interaction",
                "Resume upload": "resume_upload",
                "Resume review request": "resume_review_request",
                "Event attendance": "event_attendance",
                "LinkedIn update": "linkedin_post",
            }
            activity_type = action_map.get(action)
            if activity_type is None:
                activity_type = "discord_activity"

            payload = {
                "action": "add-activity",
                "discord_id": discord_id,
                "activity_type": activity_type,
                "details": action,
            }
            
            async with session.post(
                f"{BACKEND_API_URL}/api/bot/",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Bot-Secret": BOT_SHARED_SECRET,
                }
            ) as response:
                if response.status in (200, 201):
                    logger.info(f"✅ Successfully updated points for user {discord_id} in backend")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Failed to update points for user {discord_id} in backend: {response.status} - {error_text}")
                    return False
                    
    except Exception as e:
        logger.error(f"❌ Error updating points for user {discord_id} in backend: {e}")
        return False

async def load_cogs():
    """Load all cogs with proper error handling"""
    global cogs_loaded
    
    loaded_cogs = []
    os.makedirs('cogs', exist_ok=True)
    cog_files = [f for f in os.listdir('./cogs') if f.endswith('.py') and f != '__init__.py']
    
    for filename in cog_files:
        cog_name = filename[:-3]
        try:
            # Check if cog is already loaded
            if cog_name in bot.cogs:
                logger.info(f"✅ Cog '{cog_name}' already loaded")
                loaded_cogs.append(cog_name)
                continue
                
            await bot.load_extension(f'cogs.{cog_name}')
            loaded_cogs.append(cog_name)
            logger.info(f"✅ Successfully loaded cog: {cog_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load cog '{cog_name}': {e}")
            continue
    
    cogs_loaded = True
    return loaded_cogs

async def setup_database():
    """No local DB initialization necessary; backend is source of truth."""
    logger.info("ℹ️ Backend is source of truth (Supabase); no local DB setup")
    return True

@bot.event
async def on_ready():
    """Bot ready event with comprehensive setup"""
    global reconnect_attempts
    
    logger.info(f"🤖 Bot is online as {bot.user}")
    logger.info(f"🆔 Bot ID: {bot.user.id}")
    logger.info(f"📋 Connected to {len(bot.guilds)} server(s)")
    
    # Reset reconnect attempts on successful connection
    reconnect_attempts = 0
    
    # Setup database
    db_success = await setup_database()
    if not db_success:
        logger.error("❌ Failed to setup database, bot may not function properly")
    
    # Load cogs only if not already loaded
    if not cogs_loaded:
        loaded_cogs = await load_cogs()
        logger.info(f"🎯 All cogs loaded successfully! ({len(loaded_cogs)} cogs)")
    else:
        logger.info(f"🎯 Cogs already loaded ({len(bot.cogs)} cogs)")

    # Explicitly load the event_logger cog
    try:
        await bot.load_extension('cogs.event_logger')
        logger.info("✅ Successfully loaded event_logger cog")
    except Exception as e:
        logger.error(f"❌ Failed to load event_logger cog: {e}")
    
    # Set bot status
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"!pointshelp | {len(bot.guilds)} servers"
        )
    )

@bot.event
async def on_connect():
    """Bot connect event"""
    logger.info("🔗 Bot connected to Discord Gateway")

@bot.event
async def on_disconnect():
    """Bot disconnect event with reconnection logic"""
    global reconnect_attempts
    logger.warning("🔌 Bot disconnected from Discord Gateway")
    
    if reconnect_attempts < max_reconnect_attempts:
        reconnect_attempts += 1
        logger.info(f"🔄 Attempting to reconnect... (Attempt {reconnect_attempts}/{max_reconnect_attempts})")
        await asyncio.sleep(5)  # Wait 5 seconds before reconnecting
    else:
        logger.error("❌ Max reconnection attempts reached. Bot will not reconnect automatically.")

@bot.event
async def on_guild_join(guild):
    """Bot joined a new server"""
    logger.info(f"🎉 Bot joined new server: {guild.name} (ID: {guild.id})")

@bot.event
async def on_guild_remove(guild):
    """Bot left a server"""
    logger.info(f"👋 Bot left server: {guild.name} (ID: {guild.id})")

@bot.event
async def on_member_join(member):
    """Send personalized welcome DM to new members and register with backend"""
    try:
        # Register user with backend API using Discord User ID as authoritative identifier
        discord_id = str(member.id)
        display_name = member.display_name
        username = member.name if hasattr(member, 'name') else None
        
        # Register with backend (this ensures 1:1 mapping between Discord members and backend users)
        backend_success = await register_user_with_backend(discord_id, display_name, username)
        
        if not backend_success:
            logger.warning(f"⚠️ Failed to register user {display_name} ({discord_id}) with backend, but continuing with local operations")
        
        # Create personalized welcome embed
        embed = discord.Embed(
            title=f"🎉 Welcome to Propel2Excel, {member.display_name}!",
            description="Here's your personalized welcome message!",
            color=0x00ff00
        )
        
        embed.add_field(
            name="🏆 What is P2E?",
            value="Propel2Excel is a student-powered professional growth platform where you can network, learn, and grow together!",
            inline=False
        )
        
        embed.add_field(
            name="💰 Points System",
            value="Earn points for activities like:\n• Sending messages (+1 pt daily)\n• Attending events (+15 pts)\n• Sharing resources (+10 pts)\n• LinkedIn updates (+5 pts)",
            inline=False
        )
        
        embed.add_field(
            name="🎁 Student Dashboard",
            value="**Our Student Dashboard has everything you need:**\n• View all available rewards and incentives\n• Check your point balance and transaction history\n• Redeem rewards with your earned points\n• Track your progress and achievements\n\n**📝 You must sign up on our frontend to access these features!**\n\n[🎁 Sign Up & Access Dashboard](https://propel2excel-student-dashboard.vercel.app)\n",
            inline=False
        )
        
        embed.add_field(
            name="🚀 Getting Started",
            value="• Use `!pointshelp` to see all user commands\n• Use `!points` to check your points\n• Use `!resume` to upload resume for review\n• Use `!event <description>` to mark event attendance\n• Use `!resource <description>` to submit resources\n• Use `!linkedin <link>` to submit LinkedIn updates",
            inline=False
        )
        
        embed.set_footer(text="Welcome aboard! We're excited to see you grow with us! 🚀")
        embed.set_thumbnail(url=member.display_avatar.url if member.display_avatar else None)
        
        # Send the personalized welcome DM
        await member.send(embed=embed)
        
        logger.info(f"✅ Sent personalized welcome DM to {member.display_name} ({member.id}) and registered with backend")
        
    except discord.Forbidden:
        # User has DMs disabled
        logger.info(f"❌ Could not send welcome DM to {member.display_name} - DMs disabled")
    except Exception as e:
        logger.error(f"❌ Error sending welcome DM to {member.display_name}: {e}")


# Basic commands with error handling
@bot.command()
async def ping(ctx):
    """Test command to verify bot is working"""
    try:
        latency = round(bot.latency * 1000)
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Bot is working!",
            color=0x00ff00
        )
        embed.add_field(name="Latency", value=f"{latency}ms", inline=True)
        embed.add_field(name="Status", value="✅ Online", inline=True)
        
        await ctx.send(embed=embed)
        logger.info(f"Ping command used by {ctx.author} in {ctx.guild.name}")
        
    except Exception as e:
        logger.error(f"Error in ping command: {e}")
        await ctx.send("❌ An error occurred while processing the ping command.")

@bot.command()
async def test(ctx):
    """Test command to verify points system (backend only)."""
    try:
        user_id = str(ctx.author.id)
        embed = discord.Embed(
            title="🧪 Test Results",
            description="Testing bot functionality",
            color=0x00ff00
        )
        embed.add_field(name="User ID", value=user_id, inline=True)
        embed.add_field(name="Bot Status", value="✅ Working", inline=True)
        embed.add_field(name="Backend", value="✅ Connected", inline=True)
        await ctx.send(embed=embed)
        logger.info(f"Test command used by {ctx.author} in {ctx.guild.name}")
    except Exception as e:
        logger.error(f"Error in test command: {e}")
        await ctx.send("❌ An error occurred while processing the test command.")

@bot.command()
async def status(ctx):
    """Show bot status and loaded cogs"""
    try:
        embed = discord.Embed(
            title="🤖 Bot Status",
            description="Current bot information",
            color=0x0099ff
        )
        embed.add_field(name="Bot Name", value=bot.user.name, inline=True)
        embed.add_field(name="Latency", value=f"{round(bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="Servers", value=len(bot.guilds), inline=True)
        embed.add_field(name="Loaded Cogs", value=len(bot.cogs), inline=True)
        embed.add_field(name="Commands", value=len(bot.commands), inline=True)
        embed.add_field(name="Uptime", value=f"<t:{int(bot.start_time.timestamp())}:R>", inline=True)
        
        # Show cog names
        cog_names = list(bot.cogs.keys())
        embed.add_field(name="Cog Names", value=", ".join(cog_names) if cog_names else "None", inline=False)
        
        await ctx.send(embed=embed)
        logger.info(f"Status command used by {ctx.author} in {ctx.guild.name}")
        
    except Exception as e:
        logger.error(f"Error in status command: {e}")
        await ctx.send("❌ An error occurred while processing the status command.")

@bot.command()
@commands.has_permissions(administrator=True)
async def reloadcogs(ctx):
    """Reload all cogs (Admin only)"""
    try:
        global cogs_loaded
        
        # Unload all cogs first
        for cog_name in list(bot.cogs.keys()):
            await bot.unload_extension(f'cogs.{cog_name}')
            logger.info(f"Unloaded cog: {cog_name}")
        
        # Reset the loaded flag
        cogs_loaded = False
        
        # Reload all cogs
        loaded_cogs = await load_cogs()
        
        embed = discord.Embed(
            title="🔄 Cogs Reloaded",
            description=f"Successfully reloaded {len(loaded_cogs)} cogs",
            color=0x00ff00
        )
        embed.add_field(name="Loaded Cogs", value=", ".join(loaded_cogs), inline=False)
        
        await ctx.send(embed=embed)
        logger.info(f"Cogs reloaded by {ctx.author} in {ctx.guild.name}")
        
    except Exception as e:
        logger.error(f"Error reloading cogs: {e}")
        await ctx.send(f"❌ Error reloading cogs: {e}")

@bot.command()
async def welcome(ctx):
    """Send welcome message again as DM"""
    try:
        embed = discord.Embed(
            title=f"🎉 Welcome to Propel2Excel, {ctx.author.display_name}!",
            description="Here's your personalized welcome message!",
            color=0x00ff00
        )
        
        embed.add_field(
            name="🏆 What is P2E?",
            value="Propel2Excel is a student-powered professional growth platform where you can network, learn, and grow together!",
            inline=False
        )
        
        embed.add_field(
            name="💰 Points System",
            value="Earn points for activities like:\n• Sending messages (+1 pt daily)\n• Attending events (+15 pts)\n• Sharing resources (+10 pts)\n• LinkedIn updates (+5 pts)",
            inline=False
        )
        
        embed.add_field(
            name="🎁 Student Dashboard",
            value="**Our Student Dashboard has everything you need:**\n• View all available rewards and incentives\n• Check your point balance and transaction history\n• Redeem rewards with your earned points\n• Track your progress and achievements\n\n**📝 You must sign up on our frontend to access these features!**\n\n[🎁 Sign Up & Access Dashboard](https://propel2excel-student-dashboard.vercel.app)\n",
            inline=False
        )
        
        embed.add_field(
            name="🚀 Getting Started",
            value="• Use `!pointshelp` to see all user commands\n• Use `!points` to check your points\n• Use `!resume` to upload resume for review\n• Use `!event <description>` to mark event attendance\n• Use `!resource <description>` to submit resources\n• Use `!linkedin <link>` to submit LinkedIn updates",
            inline=False
        )
        
        embed.set_footer(text="Welcome aboard! We're excited to see you grow with us! 🚀")
        embed.set_thumbnail(url=ctx.author.display_avatar.url if ctx.author.display_avatar else None)
        
        # Send as DM instead of in channel
        try:
            await ctx.author.send(embed=embed)
            await ctx.send(f"✅ {ctx.author.mention} Check your DMs for the welcome message!")
        except discord.Forbidden:
            # If DMs are disabled, send in channel as fallback
            await ctx.send(embed=embed)
        
        logger.info(f"Welcome command used by {ctx.author} in {ctx.guild.name}")
        
    except Exception as e:
        logger.error(f"Error in welcome command: {e}")
        await ctx.send("❌ An error occurred while processing the welcome command.")

@bot.command()
@commands.has_permissions(administrator=True)
async def sendwelcome(ctx, member: discord.Member):
    """Admin command to manually send welcome DM to a user"""
    try:
        # Create personalized welcome embed
        embed = discord.Embed(
            title=f"🎉 Welcome to Propel2Excel, {member.display_name}!",
            description="Here's your personalized welcome message!",
            color=0x00ff00
        )
        
        embed.add_field(
            name="🏆 What is P2E?",
            value="Propel2Excel is a student-powered professional growth platform where you can network, learn, and grow together!",
            inline=False
        )
        
        embed.add_field(
            name="💰 Points System",
            value="Earn points for activities like:\n• Sending messages (+1 pt daily)\n• Attending events (+15 pts)\n• Sharing resources (+10 pts)\n• LinkedIn updates (+5 pts)",
            inline=False
        )
        
        embed.add_field(
            name="🎁 Student Dashboard",
            value="**Our Student Dashboard has everything you need:**\n• View all available rewards and incentives\n• Check your point balance and transaction history\n• Redeem rewards with your earned points\n• Track your progress and achievements\n\n**📝 You must sign up on our frontend to access these features!**\n\n[🎁 Sign Up & Access Dashboard](https://propel2excel-student-dashboard.vercel.app)\n",
            inline=False
        )
        
        embed.add_field(
            name="🚀 Getting Started",
            value="• Use `!pointshelp` to see all user commands\n• Use `!points` to check your points\n• Use `!resume` to upload resume for review\n• Use `!event <description>` to mark event attendance\n• Use `!resource <description>` to submit resources\n• Use `!linkedin <link>` to submit LinkedIn updates",
            inline=False
        )
        
        embed.set_footer(text="Welcome aboard! We're excited to see you grow with us! 🚀")
        embed.set_thumbnail(url=member.display_avatar.url if member.display_avatar else None)
        
        # Send the personalized welcome DM
        await member.send(embed=embed)
        
        await ctx.send(f"✅ Sent welcome DM to {member.mention}")
        logger.info(f"Admin {ctx.author} sent welcome DM to {member.display_name}")
        
    except discord.Forbidden:
        await ctx.send(f"❌ Could not send welcome DM to {member.mention} - DMs disabled")
    except Exception as e:
        await ctx.send(f"❌ Error sending welcome DM to {member.mention}: {e}")
        logger.error(f"Error in sendwelcome command: {e}")

@bot.command()
@commands.has_permissions(administrator=True)
async def registeruser(ctx, member: discord.Member):
    """Admin command to manually register a user with the backend"""
    try:
        discord_id = str(member.id)
        display_name = member.display_name
        username = member.name if hasattr(member, 'name') else None
        
        success = await register_user_with_backend(discord_id, display_name, username)
        
        if success:
            embed = discord.Embed(
                title="✅ User Registration",
                description=f"Successfully registered {member.mention} with backend",
                color=0x00ff00
            )
            embed.add_field(name="Discord ID", value=discord_id, inline=True)
            embed.add_field(name="Display Name", value=display_name, inline=True)
            if username:
                embed.add_field(name="Username", value=username, inline=True)
            
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ Failed to register {member.mention} with backend")
            
    except Exception as e:
        await ctx.send(f"❌ Error registering user: {e}")
        logger.error(f"Error in registeruser command: {e}")

@bot.command()
async def pointshelp(ctx):
    """Show available user commands for points and activities"""
    try:
        embed = discord.Embed(
            title="🎯 Propel2Excel User Commands",
            description="Commands available to all users for earning and tracking points",
            color=0x0099ff
        )
        
        # Main Earning Methods - PROMINENT
        embed.add_field(
            name="💰 MAIN WAYS TO EARN POINTS",
            value="**1. Daily Messaging:** Send messages in group chat = **+1 point per day**\n\n"
                  "**2. Submit Event Attendance:** `!event <description>` + **photo attachment** = **+15 points** (if approved)\n"
                  "   📸 **Required:** Photo proof of attendance\n"
                  "   📝 **Example:** `!event \"Attended Python workshop on web scraping\"`\n\n"
                  "**3. Share Resources:** `!resource <description>` = **+10 points** (if approved)\n"
                  "   📚 **For:** Tutorials, tools, articles, courses that help the community\n"
                  "   📝 **Example:** `!resource \"Found this amazing Python tutorial for beginners\"`\n\n"
                  "**4. LinkedIn Engagement:** `!linkedin <url> <description>` = **+5 points** (if approved)\n"
                  "   💼 **For:** Sharing P2E content, engaging with our posts, professional updates\n"
                  "   📝 **Example:** `!linkedin https://linkedin.com/posts/... \"Liked and commented on P2E's career tips\"`",
            inline=False
        )
        
        # Add spacing
        embed.add_field(
            name="\u200b",  # Zero-width space for spacing
            value="\u200b",  # Zero-width space for spacing
            inline=False
        )
        
        # User Commands - Core
        embed.add_field(
            name="👤 Core Commands",
            value="`!points` - Check your current points\n"
                  "`!pointshistory` - View your recent point-earning activities\n"
                  "`!pointvalues` - See point values for different activities\n"
                  "`!rank [user]` - Show user's rank and points\n"
                  "`!streak` - Track your engagement streaks",
            inline=False
        )
        
        # Add spacing
        embed.add_field(
            name="\u200b",  # Zero-width space for spacing
            value="\u200b",  # Zero-width space for spacing
            inline=False
        )
        
        # Resume Review System
        embed.add_field(
            name="📋 Resume Review System",
            value="`!review_status` - Check the status of your review request",
            inline=False
        )
        
        # Add spacing
        embed.add_field(
            name="\u200b",  # Zero-width space for spacing
            value="\u200b",  # Zero-width space for spacing
            inline=False
        )
        
        # Utility Commands
        embed.add_field(
            name="🔧 Utility Commands",
            value="`!link <6-digit-code>` - Link Discord account with website\n"
                  "`!ping` - Test bot connectivity\n"
                  "`!welcome` - Show welcome message again\n"
                  "`!pointshelp` - Show this help message",
            inline=False
        )
        
        # Add spacing
        embed.add_field(
            name="\u200b",  # Zero-width space for spacing
            value="\u200b",  # Zero-width space for spacing
            inline=False
        )
        
        # Coming Soon Features
        embed.add_field(
            name="🚧 Coming Soon",
            value="`!leaderboard [category]` - Show leaderboards (total, networking, learning, events, resources)\n"
                  "`!milestones` - Show available incentives and progress\n"
                  "`!shop` - View available incentives and rewards\n"
                  "`!redeem <id>` - Redeem an incentive with your points\n"
                  "`!levelup` - Show progress toward next tier/badge (placeholder)\n"
                  "`!badge` - Display earned career/professional badges (placeholder)",
            inline=False
        )
        
        embed.add_field(
            name="📊 Quick Summary",
            value="**User Commands:** 20+ commands available\n"
                  "**Prefix:** Use `!` before each command\n"
                  "**Admin Commands:** Use `!adminhelp` (Admin only)\n"
                  "**Examples:** `!points`, `!leaderboard networking`, `!redeem 1`",
            inline=False
        )
        
        embed.set_footer(text="Start earning points and unlock amazing incentives! 🎉")
        
        try:
            # Send help as DM to avoid cluttering the channel
            await ctx.author.send(embed=embed)
            # Send a brief confirmation in the channel
            await ctx.send(f"✅ {ctx.author.mention} Check your DMs for the complete help guide!")
        except discord.Forbidden:
            # If DMs are disabled, send in channel as fallback
            await ctx.send(embed=embed)
        
        logger.info(f"Points help command used by {ctx.author} in {ctx.guild.name}")
        
    except Exception as e:
        logger.error(f"Error in pointshelp command: {e}")
        await ctx.send("❌ An error occurred while processing the help command.")

@bot.command()
@commands.has_permissions(administrator=True)
async def adminhelp(ctx):
    """Show available admin commands (Admin only)"""
    try:
        embed = discord.Embed(
            title="⚙️ Propel2Excel Admin Commands",
            description="Administrative commands for managing the points system",
            color=0xff6b35
        )
        
        # Admin Commands - Points Management
        embed.add_field(
            name="⚙️ Points Management",
            value="`!addpoints <member> <amount>` - Add points to a user\n"
                  "`!removepoints <member> <amount>` - Remove points from a user\n"
                  "`!resetpoints <member>` - Reset a user's points to zero\n"
                  "`!clearwarnings <member>` - Clear warnings for a user\n"
                  "`!suspenduser <member> <minutes>` - Suspend user from earning points\n"
                  "`!unsuspenduser <member>` - Remove suspension from a user",
            inline=False
        )
        
        # Admin Commands - Statistics & Monitoring
        embed.add_field(
            name="📊 Statistics & Monitoring",
            value="`!stats` - Show bot statistics and activity\n"
                  "`!topusers [limit]` - Show top users by points\n"
                  "`!activitylog [hours]` - Show recent activity log\n"
                  "`!audit [hours] [user]` - View comprehensive activity audit logs\n"
                  "`!highlight [period]` - Highlight top contributors (week/month/all)",
            inline=False
        )
        
        # Admin Commands - Submission Reviews
        embed.add_field(
            name="📋 Submission Reviews",
            value="`!pendingresources` - View pending resource submissions\n"
                  "`!pendingevents` - View pending event submissions\n"
                  "`!pendinglinkedin` - View pending LinkedIn submissions\n"
                  "`!approveresource <user_id> <points> [notes]` - Approve resource\n"
                  "`!rejectresource <user_id> [reason]` - Reject resource\n"
                  "`!approveevent <user> [notes]` - Approve event attendance\n"
                  "`!rejectevent <user> [reason]` - Reject event attendance\n"
                  "`!approvelinkedin <user> [notes]` - Approve LinkedIn update\n"
                  "`!rejectlinkedin <user> [reason]` - Reject LinkedIn update",
            inline=False
        )
        
        # Admin Commands - Reward Management
        embed.add_field(
            name="🎁 Reward Management",
            value="`!rewards` - View all rewards and their status\n"
                  "`!enable_reward <name>` - Restock a reward (sets to 10)\n"
                  "`!disable_reward <name>` - Make reward out of stock\n"
                  "`!set_stock <amount> <name>` - Set specific stock amount",
            inline=False
        )
        
        # Admin Commands - Resume Review Management
        embed.add_field(
            name="📝 Resume Review Management",
            value="`!add_professional <name> <specialties>` - Add professional to pool\n"
                  "`!match_review <user> <professional>` - Match student with professional\n"
                  "`!review_stats` - Show resume review statistics\n"
                  "`!pending_reviews` - Show pending review requests\n"
                  "`!suggest_matches <user>` - Show professional matches for student\n"
                  "`!schedule_session <user> <professional> <time>` - Schedule review session",
            inline=False
        )
        
        # Admin Commands - User Management
        embed.add_field(
            name="👥 User Management",
            value="`!sendwelcome <member>` - Manually send welcome DM\n"
                  "`!registeruser <member>` - Manually register user with backend\n"
                  "`!checkmilestones [user]` - Manually check user milestones\n"
                  "`!verifycourse <member> <course> <points> [notes]` - Verify course completion",
            inline=False
        )
        
        # Admin Commands - System Management
        embed.add_field(
            name="🔧 System Management",
            value="`!reloadcogs` - Reload all bot cogs\n"
                  "`!adminreport` - Manually trigger admin report\n"
                  "`!list_professionals` - List available professionals",
            inline=False
        )
        
        embed.add_field(
            name="📊 Admin Summary",
            value="**Admin Commands:** 30+ commands available\n"
                  "**Permissions:** Administrator role required\n"
                  "**User Commands:** Use `!pointshelp` for user commands\n"
                  "**Examples:** `!pendingresources`, `!addpoints @user 50`, `!stats`",
            inline=False
        )
        
        embed.set_footer(text="Admin commands - Use responsibly! 🛡️")
        
        await ctx.send(embed=embed)
        logger.info(f"Admin help command used by {ctx.author} in {ctx.guild.name}")
        
    except Exception as e:
        logger.error(f"Error in adminhelp command: {e}")
        await ctx.send("❌ An error occurred while processing the admin help command.")


@bot.command()
async def link(ctx, code: str = None):
    """Link your Discord account to your website account using a 6-digit code."""
    if not code or len(code) != 6 or not code.isdigit():
        await ctx.send("Usage: `!link <6-digit code>`\nGet your code from the website profile page.")
        return
    try:
        async with aiohttp.ClientSession() as session:
            # Include Discord username for verification security
            payload = {
                "action": "link",
                "code": code,
                "discord_id": str(ctx.author.id),
                "discord_username": f"{ctx.author.name}#{ctx.author.discriminator}"
            }
            async with session.post(
                f"{BACKEND_API_URL}/api/bot/",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Bot-Secret": BOT_SHARED_SECRET,
                }
            ) as response:
                if response.status in (200, 201):
                    data = await response.json()
                    if data.get('verified'):
                        await ctx.send("✅ Successfully verified and linked your Discord account to your website account!")
                        await ctx.send("🎉 You can now use all Discord bot features and earn points!")
                    else:
                        await ctx.send("✅ Successfully linked your Discord to your website account.")
                else:
                    raw = await response.text()
                    # Log full backend error for diagnostics
                    logger.error(f"Link failed ({response.status}): {raw[:4000]}")
                    # Try to show a concise message to user without exceeding Discord limits
                    short_msg = None
                    try:
                        data = json.loads(raw)
                        short_msg = data.get('error') or data
                    except Exception:
                        pass
                    if not short_msg:
                        short_msg = f"status {response.status}"
                    # Ensure under 1800 chars to be safe
                    short = str(short_msg)
                    if len(short) > 1800:
                        short = short[:1800] + "…"
                    await ctx.send(f"❌ Linking failed: {short}")
    except Exception as e:
        await ctx.send(f"❌ Linking error: {e}")


@bot.command()
async def rank(ctx, member: discord.Member = None):
    """Show user's rank and points (backend). Defaults to caller."""
    try:
        if member is None:
            member = ctx.author
        page = 1
        while True:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BACKEND_API_URL}/api/bot/",
                    json={"action": "leaderboard", "page": page, "page_size": 50},
                    headers={"Content-Type": "application/json", "X-Bot-Secret": BOT_SHARED_SECRET},
                ) as resp:
                    if resp.status != 200:
                        await ctx.send("❌ Failed to fetch rank.")
                        return
                    data = await resp.json()
                    for item in data.get("results", []):
                        if item.get("discord_id") == str(member.id):
                            await ctx.send(f"🏅 {member.display_name} is ranked #{item.get('position')} with {item.get('total_points', 0)} points.")
                            return
                    if data.get("page") >= data.get("total_pages"):
                        break
                    page += 1
        await ctx.send(f"{member.display_name} has no points and is not on the leaderboard.")
    except Exception as e:
        logger.error(f"Rank error: {e}")
        await ctx.send("❌ Error fetching rank.")


# Error handling
@bot.event
async def on_command_error(ctx, error):
    """Global error handler"""
    if isinstance(error, commands.CommandNotFound):
        # Ignore command not found errors to reduce spam
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
        logger.warning(f"Permission denied for {ctx.author} in {ctx.guild.name}")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏰ Please wait {error.retry_after:.1f} seconds before using this command again.")
        logger.info(f"Cooldown triggered for {ctx.author} in {ctx.guild.name}")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: {error.param}")
        logger.warning(f"Missing argument for {ctx.author} in {ctx.guild.name}: {error.param}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Invalid argument provided.")
        logger.warning(f"Bad argument from {ctx.author} in {ctx.guild.name}")
    else:
        logger.error(f"Unhandled command error: {error}")
        await ctx.send("❌ An unexpected error occurred while processing your command.")

# Graceful shutdown
async def shutdown():
    """Graceful shutdown function"""
    logger.info("🛑 Shutting down bot...")
    await bot.close()

# Signal handlers for graceful shutdown
import signal
def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}, shutting down...")
    asyncio.create_task(shutdown())

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Main execution
async def main():
    """Main function to run Discord bot only"""
    try:
        logger.info("🤖 Starting Discord Bot...")
        logger.info(f"📋 Bot will use prefix: !")
        logger.info(f"🔗 Connecting to Discord...")
        
        # Start bot (no HTTP server needed)
        await bot.start(TOKEN)
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        await shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)
