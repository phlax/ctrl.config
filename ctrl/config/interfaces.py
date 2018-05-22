

from zope.interface import Interface


class IServerConfig(Interface):

    pass


class ICtrlConfig(Interface):

    def read():
        pass

    def write():
        pass


class IConfiguration(Interface):

    def configure():
        pass
