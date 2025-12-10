"""
RING-5 Web Pages
Export all page classes.
"""

from .configure_pipeline import ConfigurePipelinePage
from .data_managers import DataManagersPage
from .data_source import DataSourcePage
from .upload_data import UploadDataPage

__all__ = ["DataSourcePage", "UploadDataPage", "ConfigurePipelinePage", "DataManagersPage"]
