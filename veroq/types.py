from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Source:
    name: str = ""
    url: str = ""
    trust_level: Optional[str] = None
    verified: Optional[bool] = None


@dataclass
class Entity:
    name: str = ""
    type: Optional[str] = None
    sentiment: Optional[str] = None
    mention_count: Optional[int] = None
    ticker: Optional[str] = None
    role: Optional[str] = None


@dataclass
class Provenance:
    review_status: Optional[str] = None
    ai_contribution_pct: Optional[float] = None
    human_contribution_pct: Optional[float] = None
    confidence_score: Optional[float] = None
    bias_score: Optional[float] = None
    agents_involved: Optional[List[str]] = None


@dataclass
class Brief:
    id: Optional[str] = None
    headline: str = ""
    summary: Optional[str] = None
    body: Optional[str] = None
    confidence: Optional[float] = None
    bias_score: Optional[float] = None
    sentiment: Optional[str] = None
    counter_argument: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    sources: Optional[List[Source]] = None
    entities_enriched: Optional[List[Entity]] = None
    structured_data: Optional[Dict[str, Any]] = None
    published_at: Optional[str] = None
    review_status: Optional[str] = None
    provenance: Optional[Provenance] = None
    brief_type: Optional[str] = None
    trending: Optional[bool] = None
    topics: Optional[List[str]] = None
    entities: Optional[List[str]] = None
    impact_score: Optional[float] = None
    read_time_seconds: Optional[int] = None
    source_count: Optional[int] = None
    corrections_count: Optional[int] = None
    bias_analysis: Optional[Dict[str, Any]] = None
    full_sources: Optional[List[Dict[str, Any]]] = None


@dataclass
class FeedResponse:
    briefs: List[Brief] = field(default_factory=list)
    total: int = 0
    page: int = 1
    per_page: int = 20
    generated_at: Optional[str] = None
    agent_version: Optional[str] = None
    sources_scanned_24h: Optional[int] = None


@dataclass
class DepthMetadata:
    depth: Optional[str] = None
    search_ms: Optional[int] = None
    cross_ref_ms: Optional[int] = None
    verification_ms: Optional[int] = None
    total_ms: Optional[int] = None


@dataclass
class EntityCrossRef:
    brief_id: Optional[str] = None
    headline: Optional[str] = None
    published_at: Optional[str] = None


@dataclass
class SourceVerification:
    checked: int = 0
    accessible: int = 0
    inaccessible: int = 0


@dataclass
class SearchResponse:
    briefs: List[Brief] = field(default_factory=list)
    total: int = 0
    facets: Optional[Dict[str, Any]] = None
    related_queries: Optional[List[str]] = None
    did_you_mean: Optional[str] = None
    took_ms: Optional[int] = None
    meta: Optional[Dict[str, Any]] = None
    depth_metadata: Optional[DepthMetadata] = None


@dataclass
class ExtractResult:
    url: str = ""
    title: Optional[str] = None
    text: Optional[str] = None
    word_count: Optional[int] = None
    language: Optional[str] = None
    published_date: Optional[str] = None
    domain: Optional[str] = None
    success: bool = False
    error: Optional[str] = None


@dataclass
class ExtractResponse:
    results: List[ExtractResult] = field(default_factory=list)
    credits_used: int = 0


@dataclass
class Cluster:
    cluster_id: Optional[str] = None
    topic: str = ""
    brief_count: int = 0
    categories: Optional[List[str]] = None
    briefs: Optional[List[Brief]] = None
    latest: Optional[str] = None


@dataclass
class ClustersResponse:
    clusters: List[Cluster] = field(default_factory=list)
    period: Optional[str] = None


@dataclass
class DataPointValue:
    type: Optional[str] = None
    value: Optional[Any] = None
    context: Optional[str] = None
    entity: Optional[str] = None


@dataclass
class DataPoint:
    brief_id: Optional[str] = None
    headline: Optional[str] = None
    data_point: Optional[DataPointValue] = None
    published_at: Optional[str] = None


@dataclass
class DataResponse:
    data: List[DataPoint] = field(default_factory=list)


@dataclass
class EntitiesResponse:
    entities: List[Entity] = field(default_factory=list)


@dataclass
class SourceAnalysis:
    outlet: Optional[str] = None
    headline: Optional[str] = None
    framing: Optional[str] = None
    political_lean: Optional[str] = None
    loaded_language: Optional[List[str]] = None
    emphasis: Optional[List[str]] = None
    omissions: Optional[List[str]] = None
    sentiment: Optional[Dict[str, str]] = None
    raw_excerpt: Optional[str] = None


@dataclass
class ComparisonResponse:
    topic: Optional[str] = None
    share_id: Optional[str] = None
    polaris_brief: Optional[Brief] = None
    source_analyses: Optional[List[SourceAnalysis]] = None
    polaris_analysis: Optional[Dict[str, Any]] = None
    generated_at: Optional[str] = None


@dataclass
class ResearchSourceUsed:
    brief_id: Optional[str] = None
    headline: Optional[str] = None
    confidence: Optional[float] = None
    category: Optional[str] = None


@dataclass
class ResearchEntityCooccurrence:
    entity: Optional[str] = None
    count: Optional[int] = None


@dataclass
class ResearchEntity:
    name: Optional[str] = None
    type: Optional[str] = None
    mentions: Optional[int] = None
    co_occurs_with: Optional[List["ResearchEntityCooccurrence"]] = None


@dataclass
class ResearchMetadata:
    briefs_analyzed: int = 0
    unique_sources: int = 0
    processing_time_ms: Optional[int] = None
    models_used: Optional[List[str]] = None


@dataclass
class ResearchResponse:
    query: str = ""
    report: Optional[Dict[str, Any]] = None
    sources_used: Optional[List[ResearchSourceUsed]] = None
    entity_map: Optional[List[ResearchEntity]] = None
    sub_queries: Optional[List[str]] = None
    metadata: Optional[ResearchMetadata] = None
    structured_output: Optional[Any] = None
    structured_output_error: Optional[str] = None


@dataclass
class VerifyBrief:
    id: str = ""
    headline: str = ""
    confidence: float = 0.0
    relevance: Optional[float] = None


@dataclass
class VerifyResponse:
    claim: str = ""
    verdict: str = "unverifiable"
    confidence: float = 0.0
    summary: str = ""
    supporting_briefs: Optional[List[VerifyBrief]] = None
    contradicting_briefs: Optional[List[VerifyBrief]] = None
    nuances: Optional[str] = None
    sources_analyzed: int = 0
    briefs_matched: int = 0
    credits_used: int = 0
    cached: bool = False
    processing_time_ms: int = 0
    model_used: Optional[str] = None


def _parse_verify_brief(data):
    if isinstance(data, dict):
        return VerifyBrief(**{k: v for k, v in data.items() if k in VerifyBrief.__dataclass_fields__})
    return VerifyBrief()


def _parse_verify_response(data):
    if not isinstance(data, dict):
        return VerifyResponse()
    supporting = data.get("supporting_briefs")
    contradicting = data.get("contradicting_briefs")
    return VerifyResponse(
        claim=data.get("claim", ""),
        verdict=data.get("verdict", "unverifiable"),
        confidence=data.get("confidence", 0.0),
        summary=data.get("summary", ""),
        supporting_briefs=[_parse_verify_brief(b) for b in supporting] if isinstance(supporting, list) else None,
        contradicting_briefs=[_parse_verify_brief(b) for b in contradicting] if isinstance(contradicting, list) else None,
        nuances=data.get("nuances"),
        sources_analyzed=data.get("sources_analyzed", 0),
        briefs_matched=data.get("briefs_matched", 0),
        credits_used=data.get("credits_used", 0),
        cached=data.get("cached", False),
        processing_time_ms=data.get("processing_time_ms", 0),
        model_used=data.get("model_used"),
    )


def _parse_research_entity(data):
    if not isinstance(data, dict):
        return ResearchEntity()
    coocs = data.get("co_occurs_with")
    parsed_coocs = None
    if isinstance(coocs, list):
        parsed_coocs = [ResearchEntityCooccurrence(**{k: v for k, v in c.items() if k in ResearchEntityCooccurrence.__dataclass_fields__}) for c in coocs if isinstance(c, dict)]
    return ResearchEntity(
        name=data.get("name"),
        type=data.get("type"),
        mentions=data.get("mentions"),
        co_occurs_with=parsed_coocs,
    )


def _parse_research_response(data):
    if not isinstance(data, dict):
        return ResearchResponse()
    sources = data.get("sources_used")
    parsed_sources = None
    if isinstance(sources, list):
        parsed_sources = [ResearchSourceUsed(**{k: v for k, v in s.items() if k in ResearchSourceUsed.__dataclass_fields__}) for s in sources if isinstance(s, dict)]
    entities = data.get("entity_map")
    parsed_entities = None
    if isinstance(entities, list):
        parsed_entities = [_parse_research_entity(e) for e in entities]
    meta = data.get("metadata")
    parsed_meta = None
    if isinstance(meta, dict):
        parsed_meta = ResearchMetadata(**{k: v for k, v in meta.items() if k in ResearchMetadata.__dataclass_fields__})
    return ResearchResponse(
        query=data.get("query", ""),
        report=data.get("report"),
        sources_used=parsed_sources,
        entity_map=parsed_entities,
        sub_queries=data.get("sub_queries"),
        metadata=parsed_meta,
        structured_output=data.get("structured_output"),
        structured_output_error=data.get("structured_output_error"),
    )


def _parse_source(data):
    if isinstance(data, dict):
        return Source(**{k: v for k, v in data.items() if k in Source.__dataclass_fields__})
    return Source()


def _parse_entity(data):
    if isinstance(data, dict):
        mapped = {k: v for k, v in data.items() if k in Entity.__dataclass_fields__}
        # API returns mentions_24h; map to mention_count
        if "mention_count" not in mapped and "mentions_24h" in data:
            mapped["mention_count"] = data["mentions_24h"]
        return Entity(**mapped)
    return Entity()


def _parse_provenance(data):
    if isinstance(data, dict):
        return Provenance(**{k: v for k, v in data.items() if k in Provenance.__dataclass_fields__})
    return None


def _parse_brief(data):
    if not isinstance(data, dict):
        return Brief()
    fields = {}
    for k, v in data.items():
        if k not in Brief.__dataclass_fields__:
            continue
        if k == "sources" and isinstance(v, list):
            fields[k] = [_parse_source(s) for s in v]
        elif k == "entities_enriched" and isinstance(v, list):
            fields[k] = [_parse_entity(e) for e in v]
        elif k == "provenance" and isinstance(v, dict):
            fields[k] = _parse_provenance(v)
        else:
            fields[k] = v
    brief = Brief(**fields)
    # Auto-populate convenience fields from provenance
    if brief.provenance:
        if brief.confidence is None and brief.provenance.confidence_score is not None:
            brief.confidence = brief.provenance.confidence_score
        if brief.bias_score is None and brief.provenance.bias_score is not None:
            brief.bias_score = brief.provenance.bias_score
    return brief


def _parse_data_point_value(data):
    if isinstance(data, dict):
        return DataPointValue(**{k: v for k, v in data.items() if k in DataPointValue.__dataclass_fields__})
    return None


def _parse_data_point(data):
    if not isinstance(data, dict):
        return DataPoint()
    fields = {}
    for k, v in data.items():
        if k not in DataPoint.__dataclass_fields__:
            continue
        if k == "data_point" and isinstance(v, dict):
            fields[k] = _parse_data_point_value(v)
        else:
            fields[k] = v
    return DataPoint(**fields)


def _parse_cluster(data):
    if not isinstance(data, dict):
        return Cluster()
    fields = {}
    for k, v in data.items():
        if k not in Cluster.__dataclass_fields__:
            continue
        if k == "briefs" and isinstance(v, list):
            fields[k] = [_parse_brief(b) for b in v]
        else:
            fields[k] = v
    return Cluster(**fields)


def _parse_source_analysis(data):
    if isinstance(data, dict):
        mapped = {k: v for k, v in data.items() if k in SourceAnalysis.__dataclass_fields__}
        return SourceAnalysis(**mapped)
    return SourceAnalysis()


def _parse_depth_metadata(data):
    if isinstance(data, dict):
        return DepthMetadata(**{k: v for k, v in data.items() if k in DepthMetadata.__dataclass_fields__})
    return None


def _parse_extract_result(data):
    if isinstance(data, dict):
        return ExtractResult(**{k: v for k, v in data.items() if k in ExtractResult.__dataclass_fields__})
    return ExtractResult()
