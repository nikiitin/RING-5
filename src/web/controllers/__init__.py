"""
Web Layer Controllers (Layer 2).

Controllers orchestrate the flow between UI State, Components, and the
ApplicationAPI. They are the only layer that reads state AND calls components.

Sub-packages:
    controllers.plot — Plot lifecycle, pipeline, rendering

Architecture:
    Page → Controller  ← YOU ARE HERE
              ↕
         Component  (renders widgets, returns selections)
              ↕
        UIStateManager  (typed state access)
              ↕
          ApplicationAPI  (domain operations)
"""
