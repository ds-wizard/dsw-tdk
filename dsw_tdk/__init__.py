"""DSW Template Development Kit

Template Development Kit for `Data Stewardship Wizard`_.

.. _Data Stewardship Wizard:
   https://ds-wizard.org

"""
from dsw_tdk.cli import main
from dsw_tdk.consts import APP, VERSION

__app__ = APP
__version__ = VERSION

__all__ = ['__app__', '__version__', 'main']
