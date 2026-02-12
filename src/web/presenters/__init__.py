"""
Web Layer Presenters (Layer 3).

Presenters are **pure UI renderers**: they take data IN, render Streamlit
widgets, and return user selections. They have NO state reads, NO API calls.

Sub-packages:
    presenters.plot — Plot selection, creation, controls, pipeline, chart

Architecture:
    Page → Controller
              ↕
         Presenter  ← YOU ARE HERE
         (data in → widgets → selections out)
"""
