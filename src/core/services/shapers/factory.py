"""
Shaper Factory - Dynamic Transformation Instantiation.

Implements the Factory pattern for creating shaper instances from configuration.
Dispatches to appropriate shaper class based on type identifier, supporting
all available transformation types (filter, sort, normalize, mean, etc.).

Enables runtime shaper selection and dynamic pipeline construction.
"""

from collections.abc import Mapping, Sequence
from copy import deepcopy
from inspect import isabstract
from threading import RLock
from typing import Literal, Required, cast, get_args, get_origin, get_type_hints, is_typeddict

from src.core.common.security_limits import MAX_PIPELINE_CONFIG_STEPS
from src.core.services.shapers.impl.derive_column import DeriveColumn
from src.core.services.shapers.impl.mean import Mean
from src.core.services.shapers.impl.normalize import Normalize
from src.core.services.shapers.impl.pivot import PivotLonger, PivotWider
from src.core.services.shapers.impl.selector_algorithms.column_selector import (
    ColumnSelector,
)
from src.core.services.shapers.impl.selector_algorithms.condition_selector import (
    ConditionSelector,
)
from src.core.services.shapers.impl.selector_algorithms.group_cardinality_selector import (
    GroupCardinalitySelector,
)
from src.core.services.shapers.impl.selector_algorithms.group_predicate_selector import (
    GroupPredicateSelector,
)
from src.core.services.shapers.impl.selector_algorithms.item_selector import (
    ItemSelector,
)
from src.core.services.shapers.impl.sort import Sort
from src.core.services.shapers.impl.split_apply import SplitApply
from src.core.services.shapers.impl.transformer import Transformer
from src.core.services.shapers.shaper import Shaper


from src.core.models.shaper_models import (
    MeanShaperConfig,
    NormalizeShaperConfig,
    SortShaperConfig,
    SplitApplyShaperConfig,
    TransformerShaperConfig,
    ColumnSelectorConfig,
    ConditionSelectorConfig,
    ItemSelectorConfig,
    PivotLongerShaperConfig,
    PivotWiderShaperConfig,
    DeriveColumnShaperConfig,
    GroupCardinalitySelectorConfig,
    GroupPredicateSelectorConfig,
)
from src.core.services.shapers.definition import (
    ConfigValueBudget,
    ShaperDefinition,
    ShaperValidationError,
    ValidationBudget,
    validate_mean,
    validate_schema,
    validate_config_values,
    validate_normalize,
    validate_sort,
    validate_split_apply,
    validate_transformer,
    validate_column_selector,
    validate_condition,
    validate_item_selector,
    validate_pivot_longer,
    validate_pivot_wider,
    validate_derive_column,
    validate_group_cardinality,
    validate_group_predicate,
)


class ShaperFactory:
    """Construct strategies from one exact definition per implementation."""

    _definitions: dict[str, ShaperDefinition] = {}
    _lock = RLock()

    @classmethod
    def register(cls, definition: ShaperDefinition) -> None:
        """Register an explicit definition; identifiers, classes and labels are unique.

        Raises:
            TypeError: The definition or its TypedDict contract is malformed.
            ValueError: A name, implementation, or editor order is already registered.
        """
        # [impl->req~ring5.extension.shaper-registry~1]
        if not isinstance(definition, ShaperDefinition):
            raise TypeError("register requires a ShaperDefinition.")
        if type(definition.identifier) is not str or not definition.identifier:
            raise ValueError("A shaper identifier must be non-empty text.")
        if type(definition.label) is not str or not definition.label:
            raise ValueError("A shaper label must be non-empty text.")
        if not isinstance(definition.implementation, type) or not issubclass(
            definition.implementation, Shaper
        ):
            raise TypeError("A shaper implementation must subclass Shaper.")
        if isabstract(definition.implementation):
            raise TypeError("A shaper implementation must define its transformation call.")
        if not is_typeddict(definition.config_type) or not callable(definition.validate):
            raise TypeError("A shaper definition requires a TypedDict and a semantic validator.")
        try:
            discriminator = get_type_hints(definition.config_type, include_extras=True).get("type")
        except (NameError, TypeError) as exc:
            raise TypeError("A shaper schema must resolve all value types.") from exc
        if get_origin(discriminator) is not Required:
            raise TypeError("A shaper schema requires a Required[Literal[identifier]] type field.")
        literal = get_args(discriminator)[0]
        if get_origin(literal) is not Literal or get_args(literal) != (definition.identifier,):
            raise TypeError("A shaper schema type Literal must match its registered identifier.")
        validate_schema(definition.config_type, definition.identifier)
        if definition.display_order is not None and (
            type(definition.display_order) is not int or definition.display_order < 0
        ):
            raise ValueError("display_order must be a nonnegative integer or None.")
        with cls._lock:
            for existing in cls._definitions.values():
                if definition.identifier == existing.identifier:
                    raise ValueError(
                        f"Shaper identifier {definition.identifier!r} is already registered."
                    )
                if definition.implementation is existing.implementation:
                    raise ValueError("A shaper implementation can have only one definition.")
                if definition.label == existing.label:
                    raise ValueError(f"Shaper label {definition.label!r} is already registered.")
                if (
                    definition.display_order is not None
                    and definition.display_order == existing.display_order
                ):
                    raise ValueError("A shaper editor order is already registered.")
            cls._definitions[definition.identifier] = definition

    @classmethod
    def _snapshot(cls) -> tuple[ShaperDefinition, ...]:
        with cls._lock:
            return tuple(cls._definitions.values())

    @classmethod
    def get_definition(cls, shaper_type: object) -> ShaperDefinition:
        """Return the definition for an exact identifier."""
        with cls._lock:
            if type(shaper_type) is not str or shaper_type not in cls._definitions:
                raise ValueError(
                    f"Unknown shaper type {shaper_type!r}. Available: {cls.get_available_types()}"
                )
            return cls._definitions[shaper_type]

    @classmethod
    def validate_implementation(cls, implementation: type[Shaper], params: object) -> None:
        """Validate a constructor by exact class identity, without subclass fallback."""
        for definition in cls._snapshot():
            if definition.implementation is implementation:
                cls.validate_config(definition.identifier, params)
                return
        raise ValueError(
            f"Shaper implementation {implementation.__name__!r} has no registered definition."
        )

    @classmethod
    def validate_config(
        cls,
        shaper_type: object,
        params: object,
        *,
        require_type: bool = False,
        budget: ValidationBudget | None = None,
        depth: int = 0,
    ) -> None:
        """Validate one operation and all nested steps before construction or execution."""
        if budget is None:
            validate_config_values(params)
        shared = budget if budget is not None else ValidationBudget()
        shared.charge(depth)
        definition = cls.get_definition(shaper_type)
        definition._validate_config(params, require_type=require_type)
        if issubclass(definition.implementation, SplitApply):
            config = cast(SplitApplyShaperConfig, params)
            for group in config["groups"]:
                for step in group.get("pipeline", []):
                    if not isinstance(step, dict):
                        raise TypeError("Nested pipeline steps must be configuration objects.")
                    cls.validate_config(
                        step.get("type", ""),
                        step,
                        require_type=True,
                        budget=shared,
                        depth=depth + 1,
                    )

    @classmethod
    def validate_pipeline(cls, pipeline: object) -> tuple[dict[str, object], ...]:
        """Validate all steps, then return owned mappings with one total nesting budget."""
        if not isinstance(pipeline, Sequence) or isinstance(pipeline, (str, bytes)):
            raise TypeError("A pipeline must be an ordered sequence of shaper configurations.")
        if len(pipeline) > MAX_PIPELINE_CONFIG_STEPS:
            raise ValueError(
                f"Pipeline configuration exceeds the {MAX_PIPELINE_CONFIG_STEPS}-step limit."
            )
        budget = ValidationBudget()
        value_budget = ConfigValueBudget()
        for index, step in enumerate(pipeline):
            identifier = step.get("type") if isinstance(step, Mapping) else None
            try:
                if not isinstance(step, Mapping):
                    raise TypeError("Every pipeline step must be a configuration object.")
                validate_config_values(step, budget=value_budget)
                if not identifier:
                    raise ValueError("Every step must declare a registered shaper type.")
                cls.validate_config(identifier, step, require_type=True, budget=budget)
            except (TypeError, ValueError) as exc:
                raise ShaperValidationError(
                    f"Pipeline step {index} is invalid: {exc}",
                    step_index=index,
                    shaper_type=identifier if isinstance(identifier, str) else None,
                ) from exc
        return tuple(deepcopy(dict(step)) for step in pipeline)

    @classmethod
    def get_available_types(cls) -> list[str]:
        """Return registered identifiers in registration order."""
        with cls._lock:
            return list(cls._definitions)

    @classmethod
    def get_display_name_map(cls) -> dict[str, str]:
        """Return editor labels to identifiers in their declared display order."""
        # [impl->req~ring5.extension.shaper-registry~1]
        definitions = sorted(
            (item for item in cls._snapshot() if item.display_order is not None),
            key=lambda item: cast(int, item.display_order),
        )
        return {item.label: item.identifier for item in definitions}

    @classmethod
    def get_display_name(cls, shaper_type: str) -> str:
        """Return a registered operation's display label."""
        return cls.get_definition(shaper_type).label

    @classmethod
    def create_shaper(cls, shaper_type: str, params: Mapping[str, object]) -> Shaper:
        """Construct a strategy after validating the complete configuration."""
        # [impl->req~ring5.extension.shaper-registry~1]
        cls.validate_config(shaper_type, params)
        return cls.get_definition(shaper_type).implementation(dict(params))


for _definition in (
    ShaperDefinition("mean", Mean, "Mean Calculator", MeanShaperConfig, validate_mean, 2),
    ShaperDefinition(
        "columnSelector",
        ColumnSelector,
        "Column Selector",
        ColumnSelectorConfig,
        validate_column_selector,
        0,
    ),
    ShaperDefinition(
        "conditionSelector",
        ConditionSelector,
        "Filter",
        ConditionSelectorConfig,
        validate_condition,
        6,
    ),
    ShaperDefinition(
        "itemSelector", ItemSelector, "Item Selector", ItemSelectorConfig, validate_item_selector, 7
    ),
    ShaperDefinition(
        "normalize", Normalize, "Normalize", NormalizeShaperConfig, validate_normalize, 3
    ),
    ShaperDefinition(
        "pivotLonger",
        PivotLonger,
        "Pivot Longer (Melt)",
        PivotLongerShaperConfig,
        validate_pivot_longer,
        4,
    ),
    ShaperDefinition(
        "pivotWider", PivotWider, "Pivot Wider", PivotWiderShaperConfig, validate_pivot_wider, 5
    ),
    ShaperDefinition("sort", Sort, "Sort", SortShaperConfig, validate_sort, 1),
    ShaperDefinition(
        "splitApply",
        SplitApply,
        "Split-Apply (Per-Axis)",
        SplitApplyShaperConfig,
        validate_split_apply,
        8,
    ),
    ShaperDefinition(
        "transformer", Transformer, "Transformer", TransformerShaperConfig, validate_transformer, 9
    ),
    ShaperDefinition(
        "deriveColumn",
        DeriveColumn,
        "Derive Column",
        DeriveColumnShaperConfig,
        validate_derive_column,
        10,
    ),
    ShaperDefinition(
        "groupCardinalitySelector",
        GroupCardinalitySelector,
        "Group Cardinality Filter",
        GroupCardinalitySelectorConfig,
        validate_group_cardinality,
        11,
    ),
    ShaperDefinition(
        "groupPredicateSelector",
        GroupPredicateSelector,
        "Group Predicate Filter",
        GroupPredicateSelectorConfig,
        validate_group_predicate,
        12,
    ),
):
    ShaperFactory.register(_definition)
del _definition
