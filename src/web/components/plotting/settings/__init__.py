"""Settings components — one component per settings pill tab.

Each component renders Streamlit widgets for a single settings section
and returns a flat ``dict[str, Any]`` of configuration key-value pairs.
"""

from src.web.components.plotting.settings.advanced_settings import (  # noqa: F401
    AdvancedSettingsComponent,
)
from src.web.components.plotting.settings.axes_settings import (  # noqa: F401
    AxesSettingsComponent,
)
from src.web.components.plotting.settings.colors_settings import (  # noqa: F401
    ColorsSettingsComponent,
)
from src.web.components.plotting.settings.data_labels_settings import (  # noqa: F401
    DataLabelsSettingsComponent,
)
from src.web.components.plotting.settings.engine_settings import (  # noqa: F401
    render_engine_controls,
)
from src.web.components.plotting.settings.layout_settings import (  # noqa: F401
    LayoutSettingsComponent,
)
from src.web.components.plotting.settings.legend_settings import (  # noqa: F401
    LegendSettingsComponent,
)
from src.web.components.plotting.settings.ordering_settings import (  # noqa: F401
    render_ordering_ui,
)
from src.web.components.plotting.settings.reference_line_settings import (  # noqa: F401
    render_reference_line_ui,
)
from src.web.components.plotting.settings.shapes_settings import (  # noqa: F401
    render_shapes_ui,
)
from src.web.components.plotting.settings.typography_settings import (  # noqa: F401
    TypographySettingsComponent,
)
