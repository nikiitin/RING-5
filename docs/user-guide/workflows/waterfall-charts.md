---
layout: default
title: Explain Changes with Waterfall Charts
parent: Workflows
grand_parent: User Guide
nav_order: 15
permalink: /user-guide/workflows/waterfall-charts/
---

# Explain changes with waterfall charts

<!--
`uman~ring5.plot.waterfall.documentation~1`

Covers:
- req~ring5.plot.waterfall~1

-->

Waterfall charts explain how ordered changes produce a running result. They are useful for budgets,
performance deltas, capacity plans, and any bridge from one level to another.

## Create a waterfall chart

1. Open **Manage Plots** and create a **Waterfall Chart**.
2. Finish the data-shaping pipeline.
3. Choose the ordered step column and the numeric change-or-level column.
4. Identify any steps that set an absolute level or display a subtotal.
5. Choose whether to add a final total, connect running levels, and label the bars.

Repeated rows for the same step are represented by their mean. Use the X-axis ordering control to
place steps in their intended sequence; the source data is not modified.

## Give each step the right meaning

- An ordinary **relative step** adds its value to the current running total. Positive and negative
  contributions use distinct colors.
- An **absolute step** sets the running total to its value. Use one for a starting balance or an
  explicit reset such as a new forecast.
- A **subtotal step** displays the current running total without changing it. Its source value is
  deliberately ignored.
- The optional **final total** closes the chart at the final running level and can have a custom
  label.

A step cannot be both absolute and subtotal. RING-5 rejects that ambiguous configuration instead
of choosing one silently.

## Make the bridge easy to read

Connectors show the running level between adjacent bars. Their visibility, color, and width are
configurable. Value labels display the contribution for a relative step and the resulting level
for absolute, subtotal, and total bars. Enter a bounded Python number format such as `.2f`, `.3g`,
or `,.0f` to control those labels safely.

Increase, decrease, and absolute/total colors are independent so bar meaning remains visible in
both rendering engines. Bar width and opacity can be tuned without changing the calculations.

## Python workflow

```python
import ring5

with ring5.Session() as session:
    plot = session.create_plot(
        "waterfall",
        data=changes,
        name="Operating result bridge",
        config={
            "x": "step",
            "y": "amount",
            "waterfall_absolute": ["Opening balance", "Updated forecast"],
            "waterfall_subtotals": ["Operating subtotal"],
            "waterfall_final_total": True,
            "waterfall_total_label": "Closing result",
            "waterfall_connectors": True,
            "waterfall_show_values": True,
            "waterfall_number_format": ",.0f",
        },
    )
    interactive = session.render(plot, engine="plotly")
    publication = session.render(plot, engine="matplotlib")
```

RING-5 computes each bar's kind, start, and end before rendering. Plotly receives the equivalent
native waterfall measures, while Matplotlib receives the explicit geometry, so resets, subtotals,
totals, connectors, and labels retain the same meaning.
