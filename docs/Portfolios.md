---
title: "Portfolios"
nav_order: 10
---

# Portfolios Guide

Complete guide to saving and managing analysis portfolios in RING-5.

## Overview

Portfolios are snapshots of your complete analysis session:

- All loaded data
- All plot configurations
- All data pipelines
- All transformations
- All session state

## Saving Portfolios

### From Web Interface

1. Navigate to **Portfolio** page in sidebar
2. Click **Save Portfolio**
3. Enter portfolio name
4. Optional: Add description
5. Click **Save**

### What Gets Saved

**Data**: Current DataFrame with all columns and rows
**Plots**: All configurations, mappings, and pipelines
**Session State**: Variables and settings

### Save Location

Portfolios are saved in the `portfolios/` directory as JSON files.

## Loading Portfolios

1. Navigate to **Portfolio** page
2. Select portfolio from dropdown
3. Click **Load Portfolio**
4. Wait for restoration to complete

All data, plots, and pipelines are restored.

## Best Practices

### Naming Conventions

**Good Names**:

- `ipc_comparison_2026-02`
- `cache_miss_analysis_specjbb`
- `speedup_tx_vs_baseline`

Include analysis type, date, and focus.

### When to Save

- Completing major analysis milestone
- Before applying risky transformations
- Creating publication figures
- Sharing with collaborators
- Ending work session

## Collaboration

### Sharing Portfolios

1. Locate portfolio JSON in `portfolios/` directory
2. Share via email, cloud storage, or Git
3. Recipient places file in their `portfolios/` directory

Portfolios work well with Git version control.

## Troubleshooting

### Portfolio Won't Load

- Check JSON syntax
- Verify file permissions
- Ensure RING-5 version compatibility

### Large File Size

- Filter unnecessary rows before saving
- Select only needed columns
- Aggregate repetitive data

## Next Steps

- **Web Interface**: Learn more about the [Web Interface](Web-Interface.md)
- **Creating Plots**: Master [Plot Creation](Creating-Plots.md)
- **Data Transformations**: Explore [Shapers](Data-Transformations.md)

**Need Help?** Check [Troubleshooting](Debugging.md) or open a GitHub issue.
