from . import *

# Re-export the existing Shop cog from project root for bot.load_extension
from ..shop import Shop  # noqa: F401

async def setup(bot):
    from ..shop import Shop as RootShop
    await bot.add_cog(RootShop(bot))
