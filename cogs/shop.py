from shop import Shop as RootShop

async def setup(bot):
    await bot.add_cog(RootShop(bot))
