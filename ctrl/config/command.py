
from zope import component, interface

from ctrl.config.interfaces import IConfiguration
from ctrl.command.interfaces import ISubcommand


@interface.implementer(ISubcommand)
class ConfigSubcommand(object):

    def __init__(self, context):
        self.context = context

    async def handle(self, *args, **kwargs):
        print('Running config subcommand!')
        for name, util in component.getUtilitiesFor(IConfiguration):
            print('Configuring: %s' % name)
            util.configure()
