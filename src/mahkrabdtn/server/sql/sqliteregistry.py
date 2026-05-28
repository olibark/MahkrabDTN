from threading import RLock
from uuid import UUID
from dataclasses import dataclass, field

from mahkrabdtn.protocol.node.registration import NodeRegistration
from mahkrabdtn.protocol.states import RelayNodeState
from mahkrabdtn.tools.parsing.uuid import parse_uuid
from mahkrabdtn.server.sql.sqlite import connect_database


@dataclass(slots=True)
class SQLiteNodeRegistry:
    databasePath: str
    lock: RLock = field(default_factory=RLock, repr=False)
    
    def __post_init__(self) -> None:
        with self.lock:
            self.initialize_schema()
            
    def initialize_schema(self) -> None:
        with connect_database(self.databasePath) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS relayNodes (
                    nodeID TEXT PRIMARY KEY,
                    lastSeen TEXT NOT NULL,
                    publicKey TEXT,
                    isPolling INTEGER NOT NULL,
                    pendingMessageCount INTEGER NOT NULL
                )
                """
            )
            existingColumns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(relayNodes)").fetchall()
            }
            if "publicKey" not in existingColumns:
                connection.execute("ALTER TABLE relayNodes ADD COLUMN publicKey TEXT")
            
            oldRelayNodesExists = connection.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type = 'table' AND name = 'relay_nodes'
                """
            ).fetchone()
            if oldRelayNodesExists is not None:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO relayNodes (
                        nodeID,
                        lastSeen,
                        publicKey,
                        isPolling,
                        pendingMessageCount
                    )
                    SELECT
                        node_id,
                        last_seen_at,
                        public_key,
                        is_polling,
                        pending_message_count
                    FROM relay_nodes
                    """
                )
            
            connection.commit()
    
    def register_node(self, registration: NodeRegistration) -> RelayNodeState:
        with self.lock:
            exisitingState = self.get_node_state(registration.nodeID)
            if exisitingState is None:
                state = RelayNodeState.from_registration(registration)
                self.upsert_state(state)#
                
                return state

            exisitingState.apply_registration(registration)
            self.upsert_state(exisitingState)
            
            return exisitingState
    
    def get_node_state(self, nodeID: UUID) -> RelayNodeState | None:
        nodeID = parse_uuid(nodeID, "nodeID")
        with self.lock:
            with connect_database(self.databasePath) as connection:
                row = connection.execute(
                    """
                    SELECT nodeID, lastSeen, publicKey, isPolling, pendingMessageCount
                    FROM relayNodes
                    WHERE nodeID = ?
                    """,
                    (str(nodeID),),
                ).fetchone()
                
            if row is None: return None
            
            return RelayNodeState(
                nodeID=row["nodeID"],
                lastSeen=row["lastSeen"],
                publicKey=row["publicKey"],
                isPolling=bool(row["isPolling"]),
                pendingMessageCount=int(row["pendingMessageCount"]),
            )
    
    def set_polling_state(self, nodeID: UUID, isPolling: bool) -> RelayNodeState:
        if not isinstance(isPolling, bool): raise TypeError("isPolling must be of type bool")
        
        with self.lock:
            state = self.require_node_state(nodeID)
            state.isPolling = isPolling
            self.upsert_state(state)
            
            return state
        
    def set_pending_message_count(self, nodeID: UUID, pendingMessageCount: int) -> RelayNodeState:
        if not isinstance(pendingMessageCount, int): raise TypeError("pendingMessageCount must be of type int")
        if pendingMessageCount < 0: raise ValueError("pendingMessageCount must be positive")
        
        with self.lock:
            state = self.require_node_state(nodeID)
            state.pendingMessageCount = pendingMessageCount
            self.upsert_state(state)
            
            return state
        
    def require_node_state(self, nodeID: UUID) -> RelayNodeState:
        nodeID = parse_uuid(nodeID, "nodeID")
        
        with self.lock:
            state = self.get_node_state(nodeID)
            if state is None: raise KeyError(f"unknown nodeID: {nodeID}")
            
            return state
    
    def upsert_state(self, state: RelayNodeState) -> None:
        with connect_database(self.databasePath) as connection:
            connection.execute(
                """
                INSERT INTO relayNodes (
                    nodeID,
                    lastSeen,
                    publicKey,
                    isPolling,
                    pendingMessageCount
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(nodeID) DO UPDATE SET
                    lastSeen = excluded.lastSeen,
                    publicKey = excluded.publicKey,
                    isPolling = excluded.isPolling,
                    pendingMessageCount = excluded.pendingMessageCount
                """,
                (
                    str(state.nodeID),
                    state.lastSeen.isoformat(),
                    state.publicKey,
                    int(state.isPolling),
                    state.pendingMessageCount,
                ),
            )
            connection.commit()
