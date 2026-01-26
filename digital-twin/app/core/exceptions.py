"""
Custom exception classes for the application.

Defines domain-specific exceptions for better error handling
and more informative error messages.
"""


class GoldenRetrieverException(Exception):
    """Base exception for all application errors."""
    
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ConflictNotFoundError(GoldenRetrieverException):
    """Raised when a requested conflict is not found."""
    pass


class EmbeddingServiceError(GoldenRetrieverException):
    """Raised when embedding generation fails."""
    pass


class QdrantConnectionError(GoldenRetrieverException):
    """Raised when Qdrant connection fails."""
    pass


class QdrantQueryError(GoldenRetrieverException):
    """Raised when a Qdrant query fails."""
    pass


class SimulationError(GoldenRetrieverException):
    """Raised when simulation execution fails."""
    pass


class SimulationTimeoutError(SimulationError):
    """Raised when simulation exceeds time limit."""
    pass


class InvalidConflictDataError(GoldenRetrieverException):
    """Raised when conflict data validation fails."""
    pass


class RecommendationError(GoldenRetrieverException):
    """Raised when recommendation generation fails."""
    pass
