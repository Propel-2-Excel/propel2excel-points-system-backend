from admin import Admin as RootAdmin

async def setup(bot):
    await bot.add_cog(RootAdmin(bot))
