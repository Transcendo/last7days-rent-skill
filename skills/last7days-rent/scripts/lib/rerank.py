from __future__ import annotations

from .schema import ListingCluster


def rerank_clusters(clusters: list[ListingCluster], limit: int = 5) -> list[ListingCluster]:
    ranked = sorted(clusters, key=lambda item: (item.final_score, item.match_score), reverse=True)
    return ranked[:limit]
