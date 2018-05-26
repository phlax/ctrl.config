
from zope import component

from ctrl.core.extension import CtrlExtension
from ctrl.core.interfaces import (
    ICommandRunner, ICtrlExtension, ISubcommand)

from .command import ConfigSubcommand


class CtrlConfigExtension(CtrlExtension):

    def register_adapters(self):
        component.provideAdapter(
            factory=ConfigSubcommand,
            adapts=[ICommandRunner],
            provides=ISubcommand,
            name='config')

    async def register_utilities(self):
        pass
        # component.provideUtility(
        #    config,
        #    provides=ICtrlConfig)


# register the extension
component.provideUtility(
    CtrlConfigExtension(),
    ICtrlExtension,
    'config')
