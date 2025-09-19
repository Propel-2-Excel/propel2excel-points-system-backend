import discord
from discord.ext import commands
import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import DiscordEventLog

class EventLogger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        await DiscordEventLog.objects.acreate(
            event_type='message',
            user_id=str(message.author.id),
            channel_id=str(message.channel.id),
            message_id=str(message.id),
            metadata={'content': message.content}
        )

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return

        await DiscordEventLog.objects.acreate(
            event_type='reaction_add',
            user_id=str(user.id),
            channel_id=str(reaction.message.channel.id),
            message_id=str(reaction.message.id),
            emoji=str(reaction.emoji)
        )

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # Log when a user joins a voice or stage channel
        if not before.channel and after.channel:
            await DiscordEventLog.objects.acreate(
                event_type='voice_join',
                user_id=str(member.id),
                channel_id=str(after.channel.id)
            )

async def setup(bot):
    await bot.add_cog(EventLogger(bot))
