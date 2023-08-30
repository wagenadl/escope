ESPQ = False

if ESPQ:
    from .espqgraph import ESPGraph
else:
    from .espmgraph import ESPGraph

