"""
Web Layer Controllers (Layer 2).

Controllers orchestrate the flow between UI State, Presenters, and the
ApplicationAPI. They are the only layer that reads state AND calls presenters.

Sub-packages:
    controllers.plot — Plot lifecycle, pipeline, rendering

Architecture:
    Page → Controller  ← YOU ARE HERE
              ↕
         Presenter  (renders widgets, returns selections)
              ↕
        UIStateManager  (typed state access)
              ↕
          ApplicationAPI  (domain operations)
"""
