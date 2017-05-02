import os
import gzip
import re
from glob import iglob
from collections import OrderedDict
try:
    from urllib.request import urlopen
except ImportError:
    from urllib import urlopen

MIMETYPES = OrderedDict({
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'json': 'application/json',
    'tif': 'image/tiff',
    '': 'text/plain',
})

BLANK = (
    {'Content-Type': 'application/octet-stream'},
    b'',
)

class Tile:
    '''
    Callable class for handling individual tiles.
    Stores filepath and headers, returns them on __call__.
    '''

    def __init__(self, path, compresslevel=0):
        self.ext = path.split('.')[-1].lower()
        self.file = path
        for ext in MIMETYPES.keys():
            try:
                if ext in self.ext:
                    self.headers = {
                        'Content-Type': MIMETYPES[ext]
                    }
                    break
            except TypeError:
                pass

        self.respond = self.makerespond(compresslevel)

    def makerespond(self, compresslevel):
        if 0 < compresslevel < 10:
            self.headers.update({
                'Content-Encoding': 'gzip',
                'Vary': 'Accept-Encoding',
            })
            def respond(content):
                content = gzip.compress(
                    content,
                    compresslevel = compresslevel
                )
                try:
                    self.headers['Content-Length']
                except KeyError:
                    self.headers.update({
                        'Content-Length': len(content)
                    })
                return self.headers, content
        else:
            def respond(content):
                return self.headers, content

        return respond

    def __call__(self):
        with open(self.file, 'rb') as file:
            return self.respond(file.read())

class ProxyTile(Tile):
    '''
    Extends Tile class to handle remote tile urls and cache content locally.
    '''

    def __init__(self, url, path=None, compresslevel=0):
        super(ProxyTile, self).__init__(url, compresslevel)
        self.url = url
        self.file = path
        self.proxypass = self.makepass()

    def makepass(self):
        if self.file is None:
            def proxypass():
                return requests.get(self.url).content
        else:
            def proxypass():
                try:
                    with open(self.file, 'rb') as file:
                        return file.read()
                except FileNotFoundError:
                    content = urlopen(self.url).read()
                    dir = os.path.dirname(self.file)
                    if not os.path.isdir(dir):
                        os.makedirs(dir)
                    with open(self.file, 'wb') as file:
                        file.write(content)
                    return content
        return proxypass

    def __call__(self):
        return self.respond(self.proxypass())

class TileBeard:
    '''
    The adapter for serving a set of tiles. Is bound to dir and/or url.
    '''

    __beard = {}

    def __init__(self, path=None, url=None, template='/{}/{}/{}.png', compresslevel=0):
        self.path = path
        self.url = url
        self.template = template
        self.compresslevel = compresslevel
        if url is None and path is not None:
            stars = '*' * template.count('{}')
            for file in iglob(path+template.format(*stars)):
                self.__beard[re.sub(path, '', file)] = Tile(file, self.compresslevel)

    def __call__(self, key):
        if type(key) in (tuple, list):
            key = self.template.format(*key)
        if key in self.__beard:
            return self.__beard[key]()
        else:
            if self.url is None:
                return BLANK
            else:
                path = None
                if self.path is not None:
                    path = self.path + key
                url = self.url + key
                tile = ProxyTile(url, path, self.compresslevel)
                self.__beard[key] = tile
                return tile()
