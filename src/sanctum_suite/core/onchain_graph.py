"""Bounded provenance-preserving graph views over normalized on-chain blocks."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import networkx as nx

from sanctum_suite.core.onchain import ChainName, OnChainBlock


_MAX_GRAPH_NODES = 5_000
_MAX_GRAPH_EDGES = 10_000
_DIRECT_OBSERVATION = "directly_observed"


class OnChainGraphTooLarge(ValueError):
    """The block cannot be represented within the interactive graph limits."""


class OnChainGraphBuilder:
    def build(
        self,
        block: OnChainBlock,
        *,
        case_id: str,
        risk_assessments: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        graph = nx.MultiDiGraph()
        provenance = {
            "provider": block.source,
            "chain": block.chain.value,
            "block_hash": block.block_hash,
            "block_height": block.height,
            "observed_at": block.fetched_at.isoformat(),
            "confidence": _DIRECT_OBSERVATION,
        }
        block_node = f"block:{block.chain.value}:{block.block_hash}"
        graph.add_node(
            block_node,
            kind="block",
            label=f"{block.chain.value} block {block.height}",
            **provenance,
        )

        for transaction in block.transactions:
            tx_node = f"transaction:{block.chain.value}:{transaction.transaction_hash}"
            graph.add_node(
                tx_node,
                kind="transaction",
                label=transaction.transaction_hash,
                **provenance,
            )
            graph.add_edge(
                block_node,
                tx_node,
                relation="CONTAINS",
                **provenance,
            )
            if block.chain is ChainName.BITCOIN:
                for tx_input in transaction.inputs:
                    if tx_input.previous_transaction is None:
                        continue
                    outpoint = (
                        f"outpoint:{block.chain.value}:"
                        f"{tx_input.previous_transaction}:{tx_input.previous_output_index}"
                    )
                    graph.add_node(
                        outpoint,
                        kind="outpoint",
                        label=f"{tx_input.previous_transaction}:{tx_input.previous_output_index}",
                        **provenance,
                    )
                    graph.add_edge(
                        tx_node,
                        outpoint,
                        relation="SPENDS",
                        **provenance,
                    )
                for output in transaction.outputs:
                    output_node = (
                        f"outpoint:{block.chain.value}:"
                        f"{transaction.transaction_hash}:{output.index}"
                    )
                    graph.add_node(
                        output_node,
                        kind="output",
                        label=f"{transaction.transaction_hash}:{output.index}",
                        value_atomic=output.value_atomic,
                        unit=output.unit,
                        **provenance,
                    )
                    graph.add_edge(
                        tx_node,
                        output_node,
                        relation="CREATES",
                        value_atomic=output.value_atomic,
                        unit=output.unit,
                        **provenance,
                    )
                    if output.address is not None:
                        address_node = f"address:{block.chain.value}:{output.address}"
                        graph.add_node(
                            address_node,
                            kind="address",
                            label=output.address,
                            **provenance,
                        )
                        graph.add_edge(
                            output_node,
                            address_node,
                            relation="LOCKS_TO",
                            **provenance,
                        )
            else:
                for tx_input in transaction.inputs:
                    if tx_input.address is None:
                        continue
                    address_node = f"address:{block.chain.value}:{tx_input.address}"
                    graph.add_node(
                        address_node,
                        kind="address",
                        label=tx_input.address,
                        **provenance,
                    )
                    graph.add_edge(
                        address_node,
                        tx_node,
                        relation="INITIATES",
                        **provenance,
                    )
                for output in transaction.outputs:
                    if output.address is None:
                        continue
                    address_node = f"address:{block.chain.value}:{output.address}"
                    graph.add_node(
                        address_node,
                        kind="address",
                        label=output.address,
                        **provenance,
                    )
                    graph.add_edge(
                        tx_node,
                        address_node,
                        relation="SUBMITS_TO",
                        value_atomic=output.value_atomic,
                        unit=output.unit,
                        **provenance,
                    )

            if graph.number_of_nodes() > _MAX_GRAPH_NODES or graph.number_of_edges() > _MAX_GRAPH_EDGES:
                raise OnChainGraphTooLarge(
                    "Block exceeds the interactive graph limits; no partial graph was returned"
                )

        for assessment in risk_assessments or []:
            address = assessment.get("address")
            if not isinstance(address, str):
                continue
            address_node = f"address:{block.chain.value}:{address}"
            if not graph.has_node(address_node):
                continue
            assessment_identity = json.dumps(
                [
                    assessment.get("provider"),
                    assessment.get("report_reference"),
                    assessment.get("report_sha256"),
                    assessment.get("category"),
                ],
                separators=(",", ":"),
            )
            assessment_node = (
                "provider-assessment:"
                + hashlib.sha256(assessment_identity.encode("utf-8")).hexdigest()
            )
            graph.add_node(
                assessment_node,
                kind="provider_assessment",
                label=assessment.get("category", "provider_report"),
                provider=assessment.get("provider", "unknown"),
                provider_rating=assessment.get("provider_rating", "unknown"),
                report_reference=assessment.get("report_reference", ""),
                report_sha256=assessment.get("report_sha256", ""),
                assessed_at=assessment.get("assessed_at", ""),
                observed_at=assessment.get("imported_at", ""),
                confidence="provider_reported_unverified",
                chain=block.chain.value,
                block_hash=block.block_hash,
                block_height=block.height,
            )
            graph.add_edge(
                address_node,
                assessment_node,
                relation="HAS_REPORTED_ASSESSMENT",
                provider=assessment.get("provider", "unknown"),
                provider_rating=assessment.get("provider_rating", "unknown"),
                category=assessment.get("category", ""),
                report_reference=assessment.get("report_reference", ""),
                report_sha256=assessment.get("report_sha256", ""),
                assessed_at=assessment.get("assessed_at", ""),
                observed_at=assessment.get("imported_at", ""),
                confidence="provider_reported_unverified",
                chain=block.chain.value,
                block_hash=block.block_hash,
                block_height=block.height,
            )

        if graph.number_of_nodes() > _MAX_GRAPH_NODES or graph.number_of_edges() > _MAX_GRAPH_EDGES:
            raise OnChainGraphTooLarge(
                "Block and imported assessments exceed the interactive graph limits; no partial graph was returned"
            )

        nodes = [
            {
                "id": node_id,
                **{
                    key: str(value) if key == "value_atomic" else value
                    for key, value in attributes.items()
                },
            }
            for node_id, attributes in sorted(graph.nodes(data=True))
        ]
        edges = [
            {
                "source": source,
                "target": target,
                **{
                    key: str(value) if key == "value_atomic" else value
                    for key, value in attributes.items()
                },
            }
            for source, target, _key, attributes in sorted(
                graph.edges(keys=True, data=True),
                key=lambda edge: (edge[0], edge[1], edge[2]),
            )
        ]
        return {
            "case_id": case_id,
            "chain": block.chain.value,
            "block_hash": block.block_hash,
            "block_height": block.height,
            "source": block.source,
            "observed_at": block.fetched_at.isoformat(),
            "nodes": nodes,
            "edges": edges,
            "limitations": [
                "Graph relationships represent fields directly returned by the configured RPC node.",
                "No wallet ownership, entity attribution, illicit-activity classification, or inferred confidence is produced.",
                "Bitcoin input outpoints are not resolved to prior outputs or amounts.",
                "Ethereum transaction values are requested values; execution success and actual state changes are not fetched.",
                "Imported provider reports are not independently authenticated or verified by Sanctum Suite.",
                "The graph is a point-in-time view; an optional normalized block snapshot may be retained with the case.",
            ],
        }
