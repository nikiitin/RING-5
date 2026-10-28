"""Validate current portfolio metadata and every embedded typed table."""

from typing import Any

from src.core.common.source_contributions import validate_present_source_pair

from src.core.models.portfolio_contract import validate_portfolio_schema
from src.core.common.source_context_codec import SourceContextCodec
from src.core.services.shapers.factory import ShaperFactory
from src.core.common.typed_table_codec import TypedTableCodec
from src.core.common.plot_payload import validate_plot_fields


def validate_portfolio_document(value: dict[str, Any]) -> dict[str, Any]:
    """Validate one current document without changing its serialized content.

    Raises:
        ValueError: Metadata, plot structure or an embedded table is invalid.
    """
    validate_portfolio_schema(value)
    if {"data_csv", "data_semantics"} & value.keys() or "data" not in value:
        raise ValueError("Portfolio requires the current typed data field.")
    TypedTableCodec.decode(value["data"])
    origin = SourceContextCodec.origin_from_payload(value["loaded_origin"])
    if origin is not None:
        SourceContextCodec.encode(origin.source)
        ShaperFactory.validate_pipeline(SourceContextCodec.transformations(origin))
    if type(value.get("plots")) is not list:
        raise ValueError("Portfolio plots must be an array.")
    for plot in value["plots"]:
        if type(plot) is not dict:
            raise ValueError("Portfolio plot must be an object.")
        validate_plot_fields(plot)
        if not {"source_data", "processed_data"} <= plot.keys():
            raise ValueError("Portfolio plots require current typed source and processed data.")
        source = TypedTableCodec.decode(plot["source_data"])
        processed = TypedTableCodec.decode(plot["processed_data"])
        validate_present_source_pair(source, processed)
    return value
