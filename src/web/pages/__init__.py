"""
RING-5 Web Pages
Export all page classes.
"""
from .data_source import DataSourcePage
from .upload_data import UploadDataPage
from .configure_pipeline import ConfigurePipelinePage
from .data_managers import DataManagersPage

__all__ = ['DataSourcePage', 'UploadDataPage', 'ConfigurePipelinePage', 'DataManagersPage']
