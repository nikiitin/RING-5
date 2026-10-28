"""Parser edits complete on backend previews; dialog additions own their app run."""

import re
from unittest.mock import MagicMock, PropertyMock, patch

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import pytest

from tests.visual.pages.data_source_page import DataSourcePage


@pytest.mark.parametrize(
    ("method", "field_name", "key"),
    [
        ("fill_stats_path", "stats_path_input", "statsPath"),
        ("fill_stats_pattern", "stats_pattern_input", "statsPattern"),
    ],
)
@pytest.mark.parametrize("published", [False, True])
def test_parser_text_edit_requires_its_exact_key_owned_backend_preview(
    method: str, field_name: str, key: str, published: bool
) -> None:
    """Local input text or an unrelated matching preview value cannot acknowledge an edit."""
    page = MagicMock()
    source = DataSourcePage(page)
    field, preview, field_expectation, preview_expectation = (
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
    )
    value = 'résults  "quoted" \\ pattern\nnext'
    rendered = '"résults  "quoted" \\\\ pattern\\nnext"'
    events: list[str] = []
    field.fill.side_effect = lambda *_args: events.append("typed")
    field.press.side_effect = lambda *_args: events.append("blurred")
    field_expectation.to_have_value.side_effect = lambda *_args, **_kwargs: events.append("local")
    failure = PlaywrightTimeoutError("The requested preview key still has its prior value")

    def retained(expected: re.Pattern[str], *, timeout: int) -> None:
        assert events == ["typed", "blurred", "local"]
        assert expected.fullmatch(rendered)
        assert not expected.fullmatch(rendered.replace("résults  ", "résults "))
        assert timeout == source.RENDER_TIMEOUT
        if not published:
            raise failure

    preview_expectation.to_have_text.side_effect = retained
    with (
        patch.object(DataSourcePage, field_name, new_callable=PropertyMock, return_value=field),
        patch.object(source, "config_preview_string", return_value=preview) as find_value,
        patch.object(source, "expect_script_rerun", side_effect=AssertionError("Fragment edit")),
        patch(
            "tests.visual.pages.data_source_page.expect",
            side_effect={field: field_expectation, preview: preview_expectation}.__getitem__,
        ),
    ):
        if published:
            getattr(source, method)(value)
        else:
            with pytest.raises(PlaywrightTimeoutError, match="preview key") as caught:
                getattr(source, method)(value)
            assert caught.value is failure
    field.fill.assert_called_once_with(value)
    field.press.assert_called_once_with("Tab")
    find_value.assert_called_once_with(key)
    page.wait_for_function.assert_not_called()
    page.wait_for_timeout.assert_not_called()
    page.locator.assert_not_called()


@pytest.mark.parametrize("key", ["statsPath", "statsPattern", "name"])
def test_parser_preview_value_is_scoped_to_the_exact_rendered_key(key: str) -> None:
    """A value under a different field never enters the selected key's receipt."""
    page = MagicMock()
    source = DataSourcePage(page)
    view = MagicMock()
    with patch.object(
        DataSourcePage, "config_json_view", new_callable=PropertyMock, return_value=view
    ):
        result = source.config_preview_string(key)
    pattern = page.locator.return_value.filter.call_args.kwargs["has_text"]
    assert isinstance(pattern, re.Pattern)
    assert pattern.fullmatch(f'"{key}"')
    assert not pattern.search(f'"wrong_{key}"')
    assert not pattern.search(f'"{key}_suffix"')
    view.locator.assert_called_once_with(".variable-row")
    view.locator.return_value.filter.assert_called_once_with(
        has=page.locator.return_value.filter.return_value
    )
    assert result is view.locator.return_value.filter.return_value.locator.return_value


@pytest.mark.parametrize(
    ("duplicate", "failure_stage"),
    [
        (False, None),
        (False, "completion"),
        (False, "editor"),
        (False, "preview"),
        (False, "idle"),
        (True, None),
        (True, "warning"),
    ],
)
def test_dialog_publication_distinguishes_new_app_runs_from_visible_duplicates(
    duplicate: bool, failure_stage: str | None
) -> None:
    """New variables need an app receipt; duplicates exercise and retain their warning path."""
    page = MagicMock()
    source = DataSourcePage(page)
    name = "authored.measurement"
    previous = ["simTicks", name] if duplicate else ["simTicks"]
    button, overlay, fields, preview, cycle = (
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
    )
    variable = fields.nth.return_value
    warning = overlay.get_by_test_id.return_value
    match = preview.filter.return_value
    targets = {item: MagicMock() for item in (button, overlay, fields, variable, warning, match)}
    failure = PlaywrightTimeoutError(f"Variable publication failed at {failure_stage}")
    events: list[str] = []

    def stage(value: str) -> None:
        events.append(value)
        if value == failure_stage:
            raise failure

    cycle.__enter__.side_effect = lambda: stage("armed")
    cycle.__exit__.side_effect = lambda *_args: stage("completion")
    button.click.side_effect = lambda: stage("clicked")
    targets[warning].to_have_text.side_effect = lambda *_args, **_kwargs: stage("warning")
    targets[fields].to_have_count.side_effect = lambda *_args, **_kwargs: stage("count")
    targets[variable].to_have_value.side_effect = lambda *_args, **_kwargs: stage("editor")
    targets[match].to_have_count.side_effect = lambda *_args, **_kwargs: stage("preview")
    page.wait_for_function.side_effect = lambda *_args, **_kwargs: stage("idle")
    with (
        patch.object(
            DataSourcePage, "dialog_add_button", new_callable=PropertyMock, return_value=button
        ),
        patch.object(
            DataSourcePage, "dialog_overlay", new_callable=PropertyMock, return_value=overlay
        ),
        patch.object(
            DataSourcePage, "variable_name_inputs", new_callable=PropertyMock, return_value=fields
        ),
        patch.object(source, "expect_script_rerun", return_value=cycle) as observe,
        patch.object(source, "close_dialog", side_effect=lambda: stage("closed")) as close,
        patch.object(source, "config_preview_string", return_value=preview) as find_preview,
        patch("tests.visual.pages.data_source_page.expect", side_effect=targets.__getitem__),
    ):
        if failure_stage is None:
            source._publish_dialog_variable(name, previous)
        else:
            with pytest.raises(
                PlaywrightTimeoutError, match="Variable publication failed"
            ) as caught:
                source._publish_dialog_variable(name, previous)
            assert caught.value is failure
    expected = (
        ["clicked", "warning", "closed"] if duplicate else ["armed", "clicked", "completion"]
    ) + ["count", "editor", "preview"]
    if not duplicate:
        expected.append("idle")
    if failure_stage is not None:
        expected = expected[: expected.index(failure_stage) + 1]
    assert events == expected
    button.click.assert_called_once_with()
    if duplicate:
        observe.assert_not_called()
        targets[warning].to_have_text.assert_called_once_with(
            "Variable 'authored.measurement' already exists.", timeout=source.RENDER_TIMEOUT
        )
        assert close.call_count == int(failure_stage != "warning")
    else:
        observe.assert_called_once_with()
        close.assert_not_called()
    if "count" in events:
        targets[fields].to_have_count.assert_called_once_with(
            len(previous) + int(not duplicate), timeout=source.RENDER_TIMEOUT
        )
    if "editor" in events:
        fields.nth.assert_called_once_with(1)
        targets[variable].to_have_value.assert_called_once_with(name, timeout=source.RENDER_TIMEOUT)
    if "preview" in events:
        find_preview.assert_called_once_with("name")
        pattern = preview.filter.call_args.kwargs["has_text"]
        assert pattern.fullmatch('"authored.measurement"')
        assert not pattern.search('"prefix.authored.measurement"')
    if "idle" in events:
        assert "data-test-script-state" in page.wait_for_function.call_args.args[0]
        assert "CONNECTED" in page.wait_for_function.call_args.args[0]
        assert page.wait_for_function.call_count == 1
    else:
        page.wait_for_function.assert_not_called()
    page.wait_for_timeout.assert_not_called()


@pytest.mark.parametrize("method", ["add_manual_variable", "add_variable_from_scan"])
def test_variable_flow_captures_editor_names_before_opening_and_uses_shared_publication(
    method: str,
) -> None:
    """Duplicate admission derives from the current editor before any dialog rerun."""
    page = MagicMock()
    source = DataSourcePage(page)
    fields, field, selectbox, overlay, listbox = (
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
    )
    fields.all.return_value = [field]
    events: list[str] = []

    def current_name() -> str:
        events.append("read editor")
        return "simTicks"

    field.input_value.side_effect = current_name
    listbox.get_by_role.return_value.inner_text.return_value = "new.scalar (scalar)"

    def opened() -> None:
        assert events == ["read editor"]
        events.append("opened")

    def published(name: str, previous: list[str]) -> None:
        assert events == ["read editor", "opened"]
        assert name == "new.scalar" and previous == ["simTicks"]
        events.append("publication")

    with (
        patch.object(
            DataSourcePage, "variable_name_inputs", new_callable=PropertyMock, return_value=fields
        ),
        patch.object(
            DataSourcePage,
            "dialog_manual_type_selectbox",
            new_callable=PropertyMock,
            return_value=selectbox,
        ),
        patch.object(
            DataSourcePage,
            "dialog_raw_source_type_selectbox",
            new_callable=PropertyMock,
            return_value=selectbox,
        ),
        patch.object(
            DataSourcePage,
            "dialog_search_selectbox",
            new_callable=PropertyMock,
            return_value=selectbox,
        ),
        patch.object(
            DataSourcePage, "dialog_overlay", new_callable=PropertyMock, return_value=overlay
        ),
        patch.object(source, "open_add_variable_dialog", side_effect=opened),
        patch.object(source, "switch_dialog_to_manual"),
        patch.object(source, "fill_dialog_manual_name"),
        patch.object(source, "_open_and_select"),
        patch.object(source, "_owned_listbox", return_value=("owned", listbox)),
        patch.object(source, "wait_for_streamlit"),
        patch.object(source, "_publish_dialog_variable", side_effect=published) as publish,
        patch("tests.visual.pages.data_source_page.expect"),
    ):
        getattr(source, method)("new.scalar")
    assert events == ["read editor", "opened", "publication"]
    publish.assert_called_once_with("new.scalar", ["simTicks"])
    field.input_value.assert_called_once_with()


@pytest.mark.parametrize("selected", [False, True])
@pytest.mark.parametrize("published", [False, True])
def test_parser_strategy_waits_for_its_fragment_preview_without_a_global_cycle(
    selected: bool, published: bool
) -> None:
    """Checked strategy UI alone cannot acknowledge an unpublished backend strategy."""
    page = MagicMock()
    source = DataSourcePage(page)
    option, preview, option_expectation, preview_expectation = (
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
    )
    option.is_checked.return_value = selected
    events: list[str] = []
    option.press.side_effect = lambda *_args, **_kwargs: events.append("selected")
    option_expectation.to_be_checked.side_effect = lambda **_kwargs: events.append("checked")

    def retained(value: re.Pattern[str], *, timeout: int) -> None:
        assert events == (["checked"] if selected else ["selected", "checked"])
        assert value.fullmatch('"config_aware"')
        assert timeout == source.RENDER_TIMEOUT
        if not published:
            raise PlaywrightTimeoutError("Strategy preview retains simple")

    preview_expectation.to_have_text.side_effect = retained
    with (
        patch.object(source, "config_preview_string", return_value=preview) as find_value,
        patch.object(source, "expect_script_rerun", side_effect=AssertionError("Fragment edit")),
        patch(
            "tests.visual.pages.data_source_page.expect",
            side_effect={option: option_expectation, preview: preview_expectation}.__getitem__,
        ),
    ):
        if published:
            source._select_parser_strategy(option, "config_aware")
        else:
            with pytest.raises(PlaywrightTimeoutError, match="Strategy preview retains simple"):
                source._select_parser_strategy(option, "config_aware")
    find_value.assert_called_once_with("strategy")
    if selected:
        option.press.assert_not_called()
    else:
        option.press.assert_called_once_with("Space", timeout=source.RENDER_TIMEOUT)
    option.click.assert_not_called()
    page.wait_for_function.assert_not_called()
    page.wait_for_timeout.assert_not_called()
