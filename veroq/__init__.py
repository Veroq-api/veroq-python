__version__ = "1.0.0"

from .client import VeroqClient
from .agent import Agent, AskResult, FullResult, SubscribeEvent
from .exceptions import APIError, AuthenticationError, NotFoundError, VeroqError, RateLimitError
from .types import (
    Brief,
    Cluster,
    ClustersResponse,
    ComparisonResponse,
    DataPoint,
    DataPointValue,
    DataResponse,
    DepthMetadata,
    EntitiesResponse,
    Entity,
    EntityCrossRef,
    ExtractResponse,
    ExtractResult,
    FeedResponse,
    Provenance,
    ResearchEntity,
    ResearchMetadata,
    ResearchResponse,
    ResearchSourceUsed,
    SearchResponse,
    VerifyBrief,
    VerifyResponse,
    Source,
    SourceAnalysis,
    SourceVerification,
)

try:
    from .async_client import AsyncVeroqClient
except ImportError:
    pass

# Backwards compatibility aliases
PolarisClient = VeroqClient
PolarisError = VeroqError
try:
    AsyncPolarisClient = AsyncVeroqClient
except NameError:
    pass

__all__ = [
    "VeroqClient",
    "AsyncVeroqClient",
    "VeroqError",
    "AuthenticationError",
    "RateLimitError",
    "NotFoundError",
    "APIError",
    # Backwards compatibility
    "PolarisClient",
    "PolarisError",
    "Agent",
    "AskResult",
    "FullResult",
    "SubscribeEvent",
    "Brief",
    "Source",
    "Entity",
    "Provenance",
    "FeedResponse",
    "SearchResponse",
    "Cluster",
    "ClustersResponse",
    "DataPoint",
    "DataPointValue",
    "DataResponse",
    "EntitiesResponse",
    "ComparisonResponse",
    "SourceAnalysis",
    "ExtractResult",
    "ExtractResponse",
    "ResearchResponse",
    "ResearchEntity",
    "ResearchMetadata",
    "ResearchSourceUsed",
    "DepthMetadata",
    "EntityCrossRef",
    "SourceVerification",
    "VerifyBrief",
    "VerifyResponse",
]
