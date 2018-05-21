
from zope import component

from ctrl.command.interfaces import ICommandRunner, ISubcommand

from .config import BaseConfig
from .command import ConfigSubcommand
from .interfaces import ICtrlConfig


class CtrlConfigExtension(object):

    async def register(self, app):
        component.provideAdapter(
            factory=ConfigSubcommand,
            adapts=[ICommandRunner],
            provides=ISubcommand,
            name='config')
        config = BaseConfig()
        await config.load()
        component.provideUtility(
            config,
            provides=ICtrlConfig)
