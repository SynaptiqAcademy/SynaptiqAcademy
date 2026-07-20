"""Academic Knowledge Graph Intelligence Engine — Domain models (Phase XVII)."""
from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ── Node types (35) ───────────────────────────────────────────────────────────

class NodeType(str, Enum):
    RESEARCHER           = "researcher"
    STUDENT              = "student"
    SUPERVISOR           = "supervisor"
    INSTITUTION          = "institution"
    DEPARTMENT           = "department"
    RESEARCH_CENTER      = "research_center"
    LABORATORY           = "laboratory"
    PROJECT              = "project"
    PUBLICATION          = "publication"
    DATASET              = "dataset"
    METHOD               = "method"
    VARIABLE             = "variable"
    RESEARCH_QUESTION    = "research_question"
    HYPOTHESIS           = "hypothesis"
    DOMAIN               = "domain"
    TOPIC                = "topic"
    KEYWORD              = "keyword"
    CONCEPT              = "concept"
    JOURNAL              = "journal"
    CONFERENCE           = "conference"
    GRANT                = "grant"
    FUNDING_AGENCY       = "funding_agency"
    REVIEWER             = "reviewer"
    EDITOR               = "editor"
    PATENT               = "patent"
    COURSE               = "course"
    TEACHING_MATERIAL    = "teaching_material"
    POLICY               = "policy"
    ORGANIZATION         = "organization"
    COUNTRY              = "country"
    LANGUAGE             = "language"
    SOFTWARE             = "software"
    PROGRAMMING_LANGUAGE = "programming_language"
    STATISTICAL_METHOD   = "statistical_method"
    AI_MODEL             = "ai_model"


# ── Relationship types (26) ───────────────────────────────────────────────────

class RelType(str, Enum):
    WRITES                  = "writes"
    CITES                   = "cites"
    COLLABORATES_WITH       = "collaborates_with"
    REVIEWS                 = "reviews"
    SUPERVISES              = "supervises"
    BELONGS_TO              = "belongs_to"
    FUNDED_BY               = "funded_by"
    PUBLISHED_IN            = "published_in"
    PRESENTED_AT            = "presented_at"
    USES_METHOD             = "uses_method"
    USES_DATASET            = "uses_dataset"
    EXTENDS                 = "extends"
    CONTRADICTS             = "contradicts"
    SUPPORTS                = "supports"
    INFLUENCES              = "influences"
    SHARES_KEYWORD          = "shares_keyword"
    SHARES_METHODOLOGY      = "shares_methodology"
    SHARES_RESEARCH_INTEREST= "shares_research_interest"
    SHARES_GRANT            = "shares_grant"
    SHARES_INSTITUTION      = "shares_institution"
    TEACHES                 = "teaches"
    LEARNS                  = "learns"
    PARTICIPATES_IN         = "participates_in"
    COAUTHORS               = "coauthors"
    REFERENCES              = "references"
    IMPLEMENTS              = "implements"


class QueryScope(str, Enum):
    RESEARCHERS     = "researchers"
    PUBLICATIONS    = "publications"
    GRANTS          = "grants"
    INSTITUTIONS    = "institutions"
    TOPICS          = "topics"
    METHODS         = "methods"
    ALL             = "all"


class VizType(str, Enum):
    FULL_OVERVIEW           = "full_overview"
    RESEARCH_NETWORK        = "research_network"
    CITATION_NETWORK        = "citation_network"
    INSTITUTION_NETWORK     = "institution_network"
    GRANT_NETWORK           = "grant_network"
    METHODOLOGY_NETWORK     = "methodology_network"
    TOPIC_EVOLUTION         = "topic_evolution"
    RESEARCH_COMMUNITIES    = "research_communities"
    COLLABORATION_GRAPH     = "collaboration_graph"
    CONCEPT_MAP             = "concept_map"


# ── Core node / edge dataclasses ──────────────────────────────────────────────

def _now_str() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


@dataclass
class Node:
    node_id:   str
    node_type: NodeType
    label:     str
    properties: dict   = field(default_factory=dict)
    weight:    float   = 1.0
    created_at: str    = field(default_factory=_now_str)

    def to_dict(self) -> dict:
        return {
            "node_id":    self.node_id,
            "node_type":  self.node_type.value,
            "label":      self.label,
            "properties": self.properties,
            "weight":     self.weight,
            "created_at": self.created_at,
        }


@dataclass
class Edge:
    edge_id:    str
    source:     str
    target:     str
    rel_type:   RelType
    weight:     float  = 1.0
    properties: dict   = field(default_factory=dict)
    created_at: str    = field(default_factory=_now_str)

    def to_dict(self) -> dict:
        return {
            "edge_id":    self.edge_id,
            "source":     self.source,
            "target":     self.target,
            "rel_type":   self.rel_type.value,
            "weight":     self.weight,
            "properties": self.properties,
            "created_at": self.created_at,
        }


# ── Analytics result models ───────────────────────────────────────────────────

@dataclass
class GraphStats:
    total_nodes:     int   = 0
    total_edges:     int   = 0
    density:         float = 0.0
    avg_degree:      float = 0.0
    max_degree:      int   = 0
    node_type_counts: dict = field(default_factory=dict)
    edge_type_counts: dict = field(default_factory=dict)
    connected_components: int = 0
    largest_component_size: int = 0

    def to_dict(self) -> dict:
        return {
            "total_nodes":      self.total_nodes,
            "total_edges":      self.total_edges,
            "density":          round(self.density, 5),
            "avg_degree":       round(self.avg_degree, 2),
            "max_degree":       self.max_degree,
            "node_type_counts": self.node_type_counts,
            "edge_type_counts": self.edge_type_counts,
            "connected_components": self.connected_components,
            "largest_component_size": self.largest_component_size,
        }


@dataclass
class NodeAnalytics:
    node_id:    str
    label:      str
    node_type:  str
    degree:     int   = 0
    in_degree:  int   = 0
    out_degree: int   = 0
    pagerank:   float = 0.0
    betweenness: float = 0.0
    closeness:  float = 0.0
    centrality_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "node_id":         self.node_id,
            "label":           self.label,
            "node_type":       self.node_type,
            "degree":          self.degree,
            "in_degree":       self.in_degree,
            "out_degree":      self.out_degree,
            "pagerank":        round(self.pagerank, 6),
            "betweenness":     round(self.betweenness, 6),
            "closeness":       round(self.closeness, 6),
            "centrality_score": round(self.centrality_score, 6),
        }


@dataclass
class ResearchCommunity:
    community_id:     int
    size:             int          = 0
    dominant_topics:  list[str]    = field(default_factory=list)
    key_nodes:        list[str]    = field(default_factory=list)  # node labels
    key_node_ids:     list[str]    = field(default_factory=list)  # node_ids
    cohesion_score:   float        = 0.0
    node_ids:         list[str]    = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "community_id":    self.community_id,
            "size":            self.size,
            "dominant_topics": self.dominant_topics,
            "key_nodes":       self.key_nodes,
            "cohesion_score":  round(self.cohesion_score, 3),
        }


@dataclass
class GraphEmbedding:
    node_id:       str
    vector:        list[float]
    embedding_dim: int = 16

    def to_dict(self) -> dict:
        return {
            "node_id":       self.node_id,
            "vector":        [round(v, 6) for v in self.vector],
            "embedding_dim": self.embedding_dim,
        }


@dataclass
class EmergingTopic:
    topic:          str
    score:          float = 0.0
    growth_rate:    float = 0.0
    connected_nodes: int  = 0
    related_topics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "topic":           self.topic,
            "score":           round(self.score, 3),
            "growth_rate":     round(self.growth_rate, 3),
            "connected_nodes": self.connected_nodes,
            "related_topics":  self.related_topics,
        }


@dataclass
class HiddenCollaborator:
    node_id:          str
    label:            str
    node_type:        str
    connection_path:  list[str]       = field(default_factory=list)
    shared_interests: list[str]       = field(default_factory=list)
    score:            float           = 0.0
    reason:           str             = ""

    def to_dict(self) -> dict:
        return {
            "node_id":         self.node_id,
            "label":           self.label,
            "node_type":       self.node_type,
            "connection_path": self.connection_path,
            "shared_interests": self.shared_interests,
            "score":           round(self.score, 3),
            "reason":          self.reason,
        }


@dataclass
class KGQueryResult:
    query:      str
    scope:      str
    nodes:      list[dict]   = field(default_factory=list)
    paths:      list[list]   = field(default_factory=list)
    total:      int          = 0
    reasoning:  str          = ""

    def to_dict(self) -> dict:
        return {
            "query":     self.query,
            "scope":     self.scope,
            "nodes":     self.nodes,
            "paths":     self.paths,
            "total":     self.total,
            "reasoning": self.reasoning,
        }


@dataclass
class KnowledgeCluster:
    cluster_id:   int
    theme:        str
    node_ids:     list[str]   = field(default_factory=list)
    labels:       list[str]   = field(default_factory=list)
    coherence:    float       = 0.0
    size:         int         = 0

    def to_dict(self) -> dict:
        return {
            "cluster_id": self.cluster_id,
            "theme":      self.theme,
            "labels":     self.labels[:10],
            "coherence":  round(self.coherence, 3),
            "size":       self.size,
        }
