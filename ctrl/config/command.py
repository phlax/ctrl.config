
from zope import component, interface

from ctrl.config.interfaces import IConfiguration, ICtrlConfig
from ctrl.command.interfaces import ISubcommand


@interface.implementer(ISubcommand)
class ConfigSubcommand(object):

    def __init__(self, context):
        self.context = context

    async def handle(self, loop, command, *args, **kwargs):
        return await getattr(self, 'handle_%s' % command)(*args, **kwargs)

    async def handle_update_env(self, *args, **kwargs):
        print('Updating controller environment')
        for name, util in component.getUtilitiesFor(IConfiguration):
            print('Configuring: %s' % name)
            util.configure()

    async def handle_add_installed_modules(self, *installed_modules):
        print('Generating config')
        config = component.getUtility(ICtrlConfig)

        _installed_modules = None
        if not config.config.has_section('controller'):
            config.config.add_section('controller')
        elif config.has_option('controller', 'installed_modules'):
            _installed_modules = config.get(
                'controller', 'installed_modules').split('\n')
        _installed_modules = (
            _installed_modules
            or ['ctrl.core', 'ctrl.config', 'ctrl.command'])

        for installed in installed_modules:
            print('Adding installed %s' % installed)
            _installed_modules.append(installed)

        config.config.set(
            'controller',
            'installed',
            '\n'.join(_installed_modules))
        config.config.remove_section('DEFAULT')
        with open('/etc/controller.conf', 'w') as configfile:
            config.config.write(configfile)
