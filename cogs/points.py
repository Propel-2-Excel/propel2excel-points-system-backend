from points import Points as RootPoints

async def setup(bot):
    await bot.add_cog(RootPoints(bot))
