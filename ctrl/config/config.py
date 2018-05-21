
from configparser import ConfigParser

import os


DEFAULTS = dict(
    apps=[],
    description='',
    services='',
    socket='',
    compose='',
    service='',
    name='',
    daemons='',
    var_path='/var/lib/controller')
DEFAULTS['idle-files'] = ''


class Config(object):
    pass


class BaseConfig(Config):

    async def load(self):
        self.config = ConfigParser(DEFAULTS)
        self.config.read(os.environ.get('CFG_CTRL', '/etc/controller.conf'))

    async def dump(self):
        pass
