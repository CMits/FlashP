#!/usr/bin/env python3
"""
Convert FLASH-P network.json to Cytoscape-compatible formats.

Outputs:
1. GraphML with node/edge attributes
2. SIF (Simple Interaction Format) for quick import

Usage:
    python network_to_cytoscape.py <network_directory>
    python network_to_cytoscape.py hypocotyl_length_network
    python network_to_cytoscape.py kernel_row_number_network
"""

import json
import argparse
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.dom import minidom

from flashp_version import get_version


def load_network(network_dir: Path) -> dict:
    """Load network.json from the network directory."""
    network_file = network_dir / "network" / "network.json"
    if not network_file.exists():
        raise FileNotFoundError(f"Network file not found: {network_file}")

    import light_io  # Light: read short-key/TOON network, expand to rich (incl. evidence from doi)
    return light_io.load(network_file)


def get_node_color(node_type: str) -> str:
    """Return hex color based on node type."""
    colors = {
        'GENE': '#6495ED',           # Cornflower blue
        'HORMONE': '#90EE90',         # Light green (medical: ligand / cytokine / growth factor)
        'METABOLITE': '#FFD700',      # Gold
        'PROTEIN_COMPLEX': '#DDA0DD', # Plum
        'REGULATORY_RNA': '#FFA07A',  # Light salmon
        'ENVIRONMENT': '#87CEEB',     # Sky blue (medical: cellular context — hypoxia, serum starvation)
        'PROCESS': '#F0E68C',         # Khaki
        'PHENOTYPE': '#FF6347',       # Tomato red
        'DRUG': '#FF8C00',            # Dark orange — therapeutic agents (medical edition)
    }
    return colors.get(node_type, '#CCCCCC')


def normalize_sign(sign) -> str:
    """Normalize edge sign to string format."""
    if sign in (1, 'positive', '+'):
        return 'positive'
    elif sign in (-1, 'negative', '-'):
        return 'negative'
    return 'unknown'


def get_edge_color(sign) -> str:
    """Return hex color based on edge sign."""
    sign = normalize_sign(sign)
    if sign == 'positive':
        return '#228B22'  # Forest green
    elif sign == 'negative':
        return '#DC143C'  # Crimson
    return '#808080'  # Gray for unknown


def export_graphml(network: dict, output_file: Path):
    """
    Export network to GraphML format with attributes.
    """
    # Create root element
    graphml = ET.Element('graphml', {
        'xmlns': 'http://graphml.graphdrawing.org/xmlns',
        'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        'xsi:schemaLocation': 'http://graphml.graphdrawing.org/xmlns http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd'
    })

    # Define node attribute keys
    node_attrs = [
        ('node_type', 'string', 'type'),
        ('node_label', 'string', 'label'),
        ('node_color', 'string', 'color'),
    ]

    for key_id, key_type, attr_name in node_attrs:
        ET.SubElement(graphml, 'key', {
            'id': key_id,
            'for': 'node',
            'attr.name': attr_name,
            'attr.type': key_type
        })

    # Define edge attribute keys
    edge_attrs = [
        ('edge_sign', 'string', 'sign'),
        ('edge_color', 'string', 'color'),
        ('edge_confidence', 'string', 'confidence'),
        ('edge_mechanism', 'string', 'mechanism'),
        ('edge_doi', 'string', 'doi'),
        ('edge_evidence', 'string', 'evidence_sentence'),
    ]

    for key_id, key_type, attr_name in edge_attrs:
        ET.SubElement(graphml, 'key', {
            'id': key_id,
            'for': 'edge',
            'attr.name': attr_name,
            'attr.type': key_type
        })

    # Define graph-level attribute key for version
    ET.SubElement(graphml, 'key', {
        'id': 'graph_version',
        'for': 'graph',
        'attr.name': 'flash_p_version',
        'attr.type': 'string'
    })

    # Create graph
    graph = ET.SubElement(graphml, 'graph', {
        'id': 'G',
        'edgedefault': 'directed'
    })

    # Add Flash-P version as graph attribute
    ET.SubElement(graph, 'data', {'key': 'graph_version'}).text = get_version()

    # Add nodes
    for node in network['nodes']:
        nid = node['id']
        ntype = node.get('type', 'GENE')

        node_elem = ET.SubElement(graph, 'node', {'id': nid})

        ET.SubElement(node_elem, 'data', {'key': 'node_type'}).text = ntype
        ET.SubElement(node_elem, 'data', {'key': 'node_label'}).text = nid
        ET.SubElement(node_elem, 'data', {'key': 'node_color'}).text = get_node_color(ntype)

    # Add edges
    for i, edge in enumerate(network['edges']):
        edge_id = f"e{i}"
        edge_elem = ET.SubElement(graph, 'edge', {
            'id': edge_id,
            'source': edge['source'],
            'target': edge['target']
        })

        sign = normalize_sign(edge.get('sign', 'unknown'))
        ET.SubElement(edge_elem, 'data', {'key': 'edge_sign'}).text = sign
        ET.SubElement(edge_elem, 'data', {'key': 'edge_color'}).text = get_edge_color(sign)
        ET.SubElement(edge_elem, 'data', {'key': 'edge_confidence'}).text = edge.get('confidence', 'MEDIUM')
        ET.SubElement(edge_elem, 'data', {'key': 'edge_mechanism'}).text = edge.get('mechanism', '')

        # Extract DOI and evidence sentence from evidence field.
        # v2.0 shape: evidence = [{doi, title, authors, evidence_sentence, ...}, ...]
        # v1.0 legacy: evidence = {source: {doi}, evidence_sentence, ...}
        evidence = edge.get('evidence', {})
        doi = ''
        evidence_sentence = ''
        if isinstance(evidence, list) and evidence:
            first = evidence[0] if isinstance(evidence[0], dict) else {}
            doi = first.get('doi', '') or ''
            evidence_sentence = first.get('evidence_sentence', '') or ''
        elif isinstance(evidence, dict):
            doi = evidence.get('doi', '') or ''
            if not doi:
                source = evidence.get('source', {})
                if isinstance(source, dict):
                    doi = source.get('doi', '') or ''
            evidence_sentence = evidence.get('evidence_sentence', '') or ''

        ET.SubElement(edge_elem, 'data', {'key': 'edge_doi'}).text = doi
        ET.SubElement(edge_elem, 'data', {'key': 'edge_evidence'}).text = evidence_sentence

    # Pretty print
    xml_str = ET.tostring(graphml, encoding='unicode')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent='  ')

    # Remove extra blank lines
    lines = [line for line in pretty_xml.split('\n') if line.strip()]
    pretty_xml = '\n'.join(lines)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(pretty_xml)

    print(f"  GraphML saved: {output_file}")


def export_sif(network: dict, output_file: Path):
    """
    Export network to SIF (Simple Interaction Format).
    Format: source interaction target
    """
    lines = []

    for edge in network['edges']:
        sign = normalize_sign(edge.get('sign', 'unknown'))
        interaction = 'activates' if sign == 'positive' else 'inhibits' if sign == 'negative' else 'regulates'
        lines.append(f"{edge['source']}\t{interaction}\t{edge['target']}")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"  SIF saved: {output_file}")


def export_node_attributes(network: dict, output_file: Path):
    """
    Export node attributes as tab-delimited file for Cytoscape import.
    """
    lines = ['id\ttype\tcolor']

    for node in network['nodes']:
        nid = node['id']
        ntype = node.get('type', 'GENE')
        color = get_node_color(ntype)
        lines.append(f"{nid}\t{ntype}\t{color}")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"  Node attributes saved: {output_file}")


def export_edge_attributes(network: dict, output_file: Path):
    """
    Export edge attributes as tab-delimited file for Cytoscape import.
    """
    lines = ['source\ttarget\tsign\tconfidence\tcolor\tdoi']

    for edge in network['edges']:
        sign = normalize_sign(edge.get('sign', 'unknown'))
        color = get_edge_color(sign)
        evidence = edge.get('evidence', {})
        doi = ''
        if isinstance(evidence, list) and evidence:
            first = evidence[0] if isinstance(evidence[0], dict) else {}
            doi = first.get('doi', '') or ''
        elif isinstance(evidence, dict):
            doi = evidence.get('doi', '') or ''
            if not doi:
                source = evidence.get('source', {})
                if isinstance(source, dict):
                    doi = source.get('doi', '') or ''
        lines.append(f"{edge['source']}\t{edge['target']}\t{sign}\t{edge.get('confidence', 'MEDIUM')}\t{color}\t{doi}")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"  Edge attributes saved: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Convert FLASH-P network.json to Cytoscape formats',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python network_to_cytoscape.py hypocotyl_length_network
    python network_to_cytoscape.py kernel_row_number_network

Output files (in network/cytoscape/):
    - network.graphml       : GraphML with node/edge attributes
    - network.sif           : Simple Interaction Format
    - node_attributes.txt   : Node attributes table
    - edge_attributes.txt   : Edge attributes table
        """
    )

    parser.add_argument('network_dir', type=str, help='Network directory (e.g., hypocotyl_length_network)')

    args = parser.parse_args()

    # Resolve network directory
    network_dir = Path(args.network_dir)
    if not network_dir.is_absolute():
        network_dir = Path.cwd() / network_dir

    if not network_dir.exists():
        print(f"Error: Directory not found: {network_dir}")
        sys.exit(1)

    print(f"\nFlash-P v{get_version()} — Cytoscape Export")
    print(f"Converting network from: {network_dir}")

    # Load network
    try:
        network = load_network(network_dir)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    nodes = network.get('nodes', [])
    edges = network.get('edges', [])

    print(f"  Loaded: {len(nodes)} nodes, {len(edges)} edges")

    # Create output directory
    output_dir = network_dir / "network" / "cytoscape"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nExporting to: {output_dir}")

    # Export all formats
    export_graphml(network, output_dir / "network.graphml")
    export_sif(network, output_dir / "network.sif")
    export_node_attributes(network, output_dir / "node_attributes.txt")
    export_edge_attributes(network, output_dir / "edge_attributes.txt")

    print(f"\n{'='*60}")
    print("Cytoscape Import Instructions:")
    print("="*60)
    print("""
1. Open Cytoscape Desktop

2. Import the network:
   File -> Import -> Network from File
   Select: network.graphml

3. Apply hierarchical layout:
   Layout -> yFiles Hierarchic Layout
   OR Layout -> Hierarchical Layout

4. Apply node colors by type:
   - Go to Style panel (left side)
   - Click on 'Fill Color' property
   - Set Column: color
   - Set Mapping Type: Passthrough Mapping

5. Apply edge colors by sign:
   - Click on edge tab in Style
   - Set Stroke Color -> Column: color -> Passthrough

6. Color legend:
   - Blue (#6495ED): GENE
   - Light Green (#90EE90): HORMONE / ligand / cytokine
   - Gold (#FFD700): METABOLITE
   - Plum (#DDA0DD): PROTEIN_COMPLEX
   - Light Salmon (#FFA07A): REGULATORY_RNA (miRNA)
   - Sky Blue (#87CEEB): ENVIRONMENT / cellular context
   - Khaki (#F0E68C): PROCESS
   - Tomato (#FF6347): PHENOTYPE / readout
   - Dark Orange (#FF8C00): DRUG (medical edition)
   - Green edges: activates (positive)
   - Red edges: inhibits (negative)
""")

    print("Done!")


if __name__ == '__main__':
    main()
