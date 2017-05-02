from .tilebeard import TileBeard
import os

__version__ = '0.2.1'

__all__ = ['TileBeard']

__aiocode = '''
from .tilebeard import TileBeard

class AIOBeard(TileBeard):
    """
    TileBeard variant with async/await wrapper around it's __call__ method
    """

    def __init__(self, *args, **kwargs):
        super(AIOBeard, self).__init__(*args, **kwargs)

    async def __supercall(self, key):
        return super(AIOBeard, self).__call__(key)

    async def __call__(self, key):
        return await self.__supercall(key)
'''

try:
    # execing from string to avoid SyntaxError in setuptools
    exec(__aiocode)
    __all__.append(AIOBeard)
except SyntaxError:
    pass
