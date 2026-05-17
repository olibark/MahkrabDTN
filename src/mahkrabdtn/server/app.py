from mahkrabdtn.server.registry import InMemoryNodeRegistry


class RelayApplication:
    def __init__(
        self, 
        nodeRegistry: InMemoryNodeRegistry | None = None,
        messageStore: InMemoryNodeRegistry | None = None,
        pollInterval_ms: int = 50,
        databasePath: str | None = None,
    ) -> None:
        
        if pollInterval_ms <= 0: raise ValueError("pollInterval_ms must be positive")
        if databasePath is not None and (nodeRegistry is not None or messageStore is not None):
            raise ValueError("databasePath cannot be combined with custom registry or store")
        
        if databasePath is not None: pass