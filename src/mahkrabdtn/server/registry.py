from uuid import UUID
from threading import RLock
from dataclasses import dataclass, field

from mahkrabdtn.protocol.states import RelayNodeState
from mahkrabdtn.protocol.node.registration import NodeRegistration
from mahkrabdtn.tools.parsing.uuid import parse_uuid


@dataclass(slots=True)
class InMemoryNodeRegistry:
    nodeStates: dict[UUID, RelayNodeState] = field(default_factory=dict)
    lock: RLock = field(default_factory=RLock, repr=False)
    
    def register_node(self, registration: NodeRegistration) -> RelayNodeState:
        with self.lock:
            existingState = self.nodeStates.get(registration.nodeID)
            
            if existingState is None:
                existingState = RelayNodeState.from_registration(registration)
                self.nodeStates[registration.nodeID] = existingState
                
                return existingState
            existingState.apply_registration(registration)
            
            return existingState
        
    def get_node_state(self, nodeID: UUID) -> RelayNodeState | None:
        nodeID = parse_uuid(nodeID, "nodeID")
        with self.lock:
            return self.nodeStates.get(nodeID)
        
    def set_polling_state(self, nodeID: UUID, isPolling: bool) -> RelayNodeState:
        if not isinstance(isPolling, bool): raise TypeError("isPolling must be of type bool")
        with self.lock:
            state = self.require_node_state(nodeID)
            state.isPolling = isPolling
            
            return state
    
    def set_pending_message_count(self, nodeID: UUID, pendingMessageCount: int) -> RelayNodeState:
        if not isinstance(pendingMessageCount, int): raise TypeError("pendingMessageCount must be of type int")
        if pendingMessageCount < 0: raise ValueError("pendingMessageCount must be positive")
        
        with self.lock:
            state = self.require_node_state(nodeID)
            state.pendingMessageCount= pendingMessageCount
    
            return state
        
    def require_node_state(self, nodeID: UUID) -> RelayNodeState:
        nodeID = parse_uuid(nodeID, "nodeID")
        with self.lock:
            state = self.nodeStates.get(nodeID)
            
        if state is None: raise KeyError(f"unknown nodeID: {nodeID}")
        
        return state