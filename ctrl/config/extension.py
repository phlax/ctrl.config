
from zope import component

from ctrl.core.interfaces import (
    ICommandRunner, ICtrlConfig, ISubcommand)

from .config import BaseConfig
from .command import ConfigSubcommand


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
