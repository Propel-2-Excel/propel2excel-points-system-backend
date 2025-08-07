from . import *

# Re-export the existing Points cog from project root for bot.load_extension
from ..points import Points  # noqa: F401

async def setup(bot):
    from ..points import Points as RootPoints
    await bot.add_cog(RootPoints(bot))
