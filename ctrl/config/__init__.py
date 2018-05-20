
from zope import component

from ctrl.core.interfaces import ICtrlExtension
from .extension import CtrlConfigExtension


# register the extension
component.provideUtility(
    CtrlConfigExtension(),
    ICtrlExtension,
    'config')
