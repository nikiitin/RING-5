"""
RING-5 Parsing Module — Layer A.

Multi-simulator parsing subsystem. Backends register with
``SimulatorRegistry`` (``registry.py``) and implement the
``SimulationParser`` protocol (``parser_protocol.py``); the gem5 backend
lives in ``gem5/`` and auto-registers when ``registry`` is imported.

Consumers reach a backend through ``SimulatorRegistry.get_parser(name)``,
never by importing a concrete implementation directly.
"""
