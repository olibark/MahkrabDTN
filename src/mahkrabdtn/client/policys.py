from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass(slots=True)
class RelayRetryPolicy:
    maxAttempts: int = 5
    baseBackoff: float = 0.1
    maxBackoff: float = 1.0
    backoffMultiplier: float = 2.0
    jitter: float = 0.1
    
    def __post_init__(self) -> None:
        if self.maxAttempts <= 0: raise ValueError(f"Max attepmts must be positive")
        if self.baseBackoff < 0: raise ValueError(f"base backoff must be positive")
        if self.maxBackoff < 0: raise ValueError(f"max backoff must be positive")
        if self.backoffMultiplier < 0: raise ValueError(f"backoff multiplier must be positive")
        if self.jitter < 0: raise ValueError(f"jitter must be positive")
        if self.maxBackoff < self.baseBackoff: raise ValueError(f"max backoff must be greater than equal to base backoff")
   
        
@dataclass(slots=True)
class ProcessedMessageRetentionPolicy:
    maxAge: timedelta = timedelta(days=30)
    maxEntries: int = 10000

    def __post_init__(self) -> None:
        if self.maxAge <= timedelta(0): raise ValueError("max age must be positive")
        if self.maxEntries <= 0: raise ValueError("max entries must be positive")
        