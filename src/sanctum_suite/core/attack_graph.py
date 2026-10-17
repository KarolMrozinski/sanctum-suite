import networkx as nx
from typing import List, Dict, Any


class AttackGraphEngine:
    """Silnik modelowania wielostopniowych grafów zależności ataku i ścieżek infiltracji."""

    def build_attack_graph(self, target: str, open_ports: List[Dict[str, Any]], shadow_vulns: List[Dict[str, Any]]) -> Dict[str, Any]:
        G = nx.DiGraph()

        # Węzeł główny
        G.add_node(target, type="TARGET_HOST")

        # Rejestracja otwartych portów
        for p in open_ports:
            port_node = f"Port:{p.get('port')}"
            G.add_node(port_node, type="OPEN_PORT", service=p.get("service"))
            G.add_edge(target, port_node, relation="EXPOSES")

        # Rejestracja podatności
        for v in shadow_vulns:
            vuln_node = f"Vuln:{v.get('issue')}"
            G.add_node(vuln_node, type="VULNERABILITY", severity=v.get("severity", "HIGH"))
            
            # Połączenie z odpowiednim portem lub dostawcą
            G.add_edge("Port:11434" if any(p.get("port") == 11434 for p in open_ports) else target, vuln_node, relation="EXPLOITS")

        nodes = [{"id": n, **G.nodes[n]} for n in G.nodes()]
        edges = [{"source": u, "target": v, **G.edges[u, v]} for u, v in G.edges()]

        return {
            "nodes_count": len(nodes),
            "edges_count": len(edges),
            "graph_data": {
                "nodes": nodes,
                "edges": edges,
            },
        }