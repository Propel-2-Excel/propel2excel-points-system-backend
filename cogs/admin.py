from . import *

# Re-export the existing Admin cog from project root for bot.load_extension
from ..admin import Admin  # noqa: F401

async def setup(bot):
    from ..admin import Admin as RootAdmin
    await bot.add_cog(RootAdmin(bot))
