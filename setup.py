from setuptools import setup
from tilebeard.__init__ import __version__

setup(
    name = 'tilebeard',
    version = __version__,
    description = 'A minimal WMTS adapter for web frameworks.',
    url = 'https://github.com/olegsson/tilebeard',
    author = 'olegsson',
    author_email = 'luka.olegsson@gmail.com',
    license = 'MIT',
    packages = ['tilebeard'],
    zip_safe = False
)
