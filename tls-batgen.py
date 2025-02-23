#!/usr/bin/env python
# Version 1.1.5
# Author: Zenrath
# Developed for "Last Starship version: PC - ALPHA13D - STEAM"

version = "1.1.5"

import os
import re
import shlex
import glob
import copy
import sys

def quote_if_needed(s):
    """
    If the given string s contains spaces, return it surrounded by double quotes.
    Otherwise, return it unchanged.
    """
    s = str(s)
    if " " in s:
        return f'"{s}"'
    return s

class Node:
    def __init__(self, tag=None):
        self.tag = tag            # The node identifier.
        self.attributes = []      # List of (key, value) tuples.
        self.children = []        # List of child Node objects.
        
    def __repr__(self):
        return (f"Node(tag={self.tag!r}, attributes={self.attributes!r}, "
                f"children={self.children!r})")
        
    def to_string(self, indent=0):
        ind = "    " * indent
        tag_str = quote_if_needed(self.tag) if self.tag is not None else ""
        
        # Prepare a horizontal candidate for attributes.
        horiz_attrs = ""
        if self.attributes:
            horiz_attrs = "  ".join(f"{quote_if_needed(k)} {quote_if_needed(v)}" for k, v in self.attributes)
        
        if self.children:
            horiz_header = f"{ind}BEGIN {tag_str}      {horiz_attrs}" if horiz_attrs else f"{ind}BEGIN {tag_str}"
            use_vertical = len(horiz_header) > 220
        else:
            horiz_line = f"{ind}BEGIN {tag_str}      {horiz_attrs}  END" if horiz_attrs else f"{ind}BEGIN {tag_str}  END"
            use_vertical = len(horiz_line) > 220
        
        lines = []
        if self.children:
            if not use_vertical and horiz_attrs:
                lines.append(horiz_header)
            else:
                header = f"{ind}BEGIN {tag_str}" if tag_str else f"{ind}BEGIN"
                lines.append(header)
                for key, val in self.attributes:
                    lines.append(f"{ind}    {quote_if_needed(key)} {quote_if_needed(val)}")
            for child in self.children:
                lines.append(child.to_string(indent + 1))
            lines.append(f"{ind}END")
            return "\n".join(lines)
        else:
            if not use_vertical and horiz_attrs:
                return horiz_line
            else:
                header = f"{ind}BEGIN {tag_str}" if tag_str else f"{ind}BEGIN"
                lines.append(header)
                for key, val in self.attributes:
                    lines.append(f"{ind}    {quote_if_needed(key)} {quote_if_needed(val)}")
                lines.append(f"{ind}END")
                return "\n".join(lines)

def tokenize_attributes(text):
    tokens = shlex.split(text)
    pairs = []
    it = iter(tokens)
    for token in it:
        try:
            value = next(it)
        except StopIteration:
            value = ""
        pairs.append((token, value))
    return pairs

def parse_node(lines, start_index=0):
    i = start_index
    line = lines[i].strip()
    if not line.startswith("BEGIN"):
        raise ValueError(f"Expected 'BEGIN' at line {i+1}: {line}")
        
    if "END" in line:
        pattern = r'^\s*BEGIN\s+(?:"([^"]+)"|(\S+))\s*(.*?)\s*END\s*$'
        m = re.match(pattern, line)
        if not m:
            raise ValueError(f"Malformed inline node at line {i+1}: {line}")
        tag = m.group(1) if m.group(1) is not None else m.group(2)
        attr_text = m.group(3)
        node = Node(tag)
        if attr_text:
            node.attributes = tokenize_attributes(attr_text)
        return node, i + 1
    
    header_str = line[len("BEGIN"):].strip()
    tokens = shlex.split(header_str)
    tag = tokens[0] if tokens else None
    node = Node(tag)
    if len(tokens) > 1:
        attr_text = " ".join(tokens[1:])
        node.attributes = tokenize_attributes(attr_text)
    i += 1
    while i < len(lines):
        current = lines[i].strip()
        if current.startswith("END"):
            i += 1
            return node, i
        elif current.startswith("BEGIN"):
            child, i = parse_node(lines, i)
            node.children.append(child)
        else:
            if current:
                node.attributes.extend(tokenize_attributes(current))
            i += 1
    raise ValueError("Missing END for node starting at line {}".format(start_index+1))

def parse_file(text):
    lines = text.splitlines()
    header_attrs = []
    nodes = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if i == 0 and line.strip() == "":
            i += 1
            continue
        if not line.strip():
            i += 1
            continue
        if not line.strip().startswith("BEGIN"):
            header_attrs.extend(tokenize_attributes(line))
            i += 1
        else:
            node, i = parse_node(lines, i)
            nodes.append(node)
    return header_attrs, nodes

def write_header_attrs(header_attrs, file_obj):
    if header_attrs:
        max_key_len = max(len(key) for key, _ in header_attrs)
        for key, val in header_attrs:
            file_obj.write(f"{quote_if_needed(key):<{max_key_len+2}} {quote_if_needed(val)}\n")

def write_file(header_attrs, nodes, filepath):
    with open(filepath, "w") as f:
        f.write("\n")
        if header_attrs:
            write_header_attrs(header_attrs, f)
        for node in nodes:
            f.write(node.to_string() + "\n")

def process_space_file(input_filepath):
    with open(input_filepath, "r") as f:
        file_text = f.read()
    return parse_file(file_text)

def process_ship_file(input_filepath):
    with open(input_filepath, "r") as f:
        file_text = f.read()
    return parse_file(file_text)

def set_attr(attributes, key, value):
    updated = []
    found = False
    for k, v in attributes:
        if k.lower() == key.lower():
            updated.append((k, value))
            found = True
        else:
            updated.append((k, v))
    if not found:
        updated.append((key, value))
    return updated

def remove_attributes(attributes, keys_to_remove):
    return [(k, v) for (k, v) in attributes if k not in keys_to_remove]

def update_related_ids(ship_node, target_old, target_new):
    excluded = {"Id", "NextId", "NetworkId", "JobId", "CrewJobId", "LayerId"}
    for idx, (k, v) in enumerate(ship_node.attributes):
        if ((k.endswith("Id") and k not in excluded) or (k == "Carrying")):
            if v == target_old:
                ship_node.attributes[idx] = (k, target_new)
    for child in ship_node.children:
        update_related_ids(child, target_old, target_new)

# Two-pass ID update functions:
# assign_new_ids now skips updating the id of a node if its tag is "network".
def assign_new_ids(node, next_id, mapping, inside_network=False):
    if node.tag and node.tag.lower() == "network":
        # Do not update the id attribute of a Network node.
        for child in node.children:
            assign_new_ids(child, next_id, mapping, inside_network=False)
    else:
        for idx, (k, v) in enumerate(node.attributes):
            if k.lower() == "id":
                old_value = v
                new_value = str(next_id[0])
                node.attributes[idx] = (k, new_value)
                mapping[old_value] = new_value
                next_id[0] += 1
        for child in node.children:
            assign_new_ids(child, next_id, mapping, inside_network)
            
def apply_related_id_mapping(node, mapping):
    excluded = {"Id", "NextId", "NetworkId", "JobId", "CrewJobId", "LayerId"}
    new_attrs = []
    for k, v in node.attributes:
        if ((k.endswith("Id") and k not in excluded) or (k == "Carrying")) and v in mapping:
            new_attrs.append((k, mapping[v]))
        else:
            new_attrs.append((k, v))
    node.attributes = new_attrs
    for child in node.children:
        apply_related_id_mapping(child, mapping)

def update_ids(node, next_id, inside_network=False):
    mapping = {}
    assign_new_ids(node, next_id, mapping, inside_network)
    apply_related_id_mapping(node, mapping)

def remove_workqueue(node):
    # Remove any child whose tag is "workqueue" (case-insensitive)
    node.children = [child for child in node.children if not (child.tag and child.tag.lower() == "workqueue")]
    for child in node.children:
        remove_workqueue(child)

def clear_crew_attributes(node):
    for idx in range(len(node.attributes) - 1, -1, -1):
        k, v = node.attributes[idx]
        if k == "Type" and v == "CrewMember":
            node.attributes = remove_attributes(node.attributes, {"JobId", "State"})
            break
    for child in node.children:
        clear_crew_attributes(child)

def remove_entities_recursively(node):
    # Remove any attribute named "Entities" (case-insensitive) from this node.
    node.attributes = [(k, v) for k, v in node.attributes if k.lower() != "entities"]
    for child in node.children:
        remove_entities_recursively(child)

def remove_entities_from_habitation(node):
    # If node is a Habitation node, remove "Entities" from all its descendant nodes.
    if node.tag and node.tag.lower() == "habitation":
        for child in node.children:
            remove_entities_recursively(child)
    for child in node.children:
        remove_entities_from_habitation(child)

def calc_offset(n):
    if n == 0:
        return 0
    elif n % 2 == 1:
        return ((n + 1) // 2) * 100
    else:
        return -(n // 2) * 100

def create_layers_for_ship(ship_filepath):
    header, nodes = process_ship_file(ship_filepath)
    base = os.path.splitext(os.path.basename(ship_filepath))[0]
    m = re.match(r'^(\d+)\.([^.]+)\.([^.]+)\.([^.]+)$', base)
    if not m:
        sys.stderr.write(f"Error: Filename '{os.path.basename(ship_filepath)}' does not conform to expected format: <count>.<ship-name>.<strategy>.<faction>.ship\n")
        sys.exit(1)
    copies, ship_name, strategy, faction = m.groups()
    try:
        copies_int = int(copies)
        if copies_int < 1:
            sys.stderr.write(f"Error: <count> in filename '{os.path.basename(ship_filepath)}' must be an integer ≥ 1\n")
            sys.exit(1)
    except ValueError:
        sys.stderr.write(f"Error: <count> in filename '{os.path.basename(ship_filepath)}' must be an integer\n")
        sys.exit(1)
    if not re.match(r'^[A-Za-z0-9 \-]+$', ship_name):
        sys.stderr.write(f"Error: <ship-name> in filename '{os.path.basename(ship_filepath)}' contains invalid characters. Allowed: alphanumeric, space, and '-'\n")
        sys.exit(1)
    if faction not in {"FriendlyShip", "HostileShip"}:
        sys.stderr.write(f"Error: <faction> in filename '{os.path.basename(ship_filepath)}' must be 'FriendlyShip' or 'HostileShip'\n")
        sys.exit(1)
    allowed_strategies = {"StrategyVeryCloseOrbit", "CloseRangeAggressive", "MediumRangeOrbit", "LongRangeSniper", "FastMovingJet"}
    if strategy not in allowed_strategies:
        sys.stderr.write(f"Warning: <strategy> in filename '{os.path.basename(ship_filepath)}' is '{strategy}', which is not one of the allowed values: {', '.join(allowed_strategies)}\n")
        # Continue despite the warning.
    
    layer = Node("Layer")
    layer.attributes.extend(header)
    layer.attributes = set_attr(layer.attributes, "Name", ship_name)
    layer.attributes = set_attr(layer.attributes, "Type", faction)
    layer.attributes = remove_attributes(layer.attributes, {"TimeIndex", "SaveVersion"})
    for node in nodes:
        layer.children.append(node)
    
    # Add a ShipAI sub-node with Strategy set to <strategy>, Engaged set to "true",
    # Broadside set to "-1"
    ship_ai = Node("ShipAI")
    ship_ai.attributes = set_attr([], "Strategy", strategy)
    ship_ai.attributes = set_attr(ship_ai.attributes, "Engaged", "true")
    ship_ai.attributes = set_attr(ship_ai.attributes, "Broadside", "-1")
    layer.children.append(ship_ai)
    
    layers = []
    for i in range(1, copies_int + 1):
        new_layer = copy.deepcopy(layer)
        if copies_int > 1:
            base_name = ""
            for k, v in new_layer.attributes:
                if k.lower() == "name":
                    base_name = v
                    break
            new_name = f"{base_name}-{i}"
            new_layer.attributes = set_attr(new_layer.attributes, "Name", new_name)
        new_layer.attributes = remove_attributes(new_layer.attributes, {"TimeIndex", "SaveVersion"})
        layers.append(new_layer)
    return layers

def remove_newship_friendly(nodes):
    new_nodes = []
    for node in nodes:
        node.children = remove_newship_friendly(node.children)
        name_val = None
        type_val = None
        for k, v in node.attributes:
            if k.lower() == "name":
                name_val = v
            if k.lower() == "type":
                type_val = v
        if not (name_val == "NEWSHIP" and type_val == "FriendlyShip"):
            new_nodes.append(node)
    return new_nodes

def update_shipai_layer_attribute(layer):
    layer_id = None
    for k, v in layer.attributes:
        if k.lower() == "id":
            layer_id = v
            break
    if layer_id is not None:
        for child in layer.children:
            if child.tag and child.tag.lower() == "shipai":
                child.attributes = set_attr(child.attributes, "Layer", layer_id)
                break

def main():
    # Print startup header.
    print(f"TLS v: PC - ALPHA13D - STEAM, Script v: {version} by Zenrath")
    
    # Locate .space file, ignoring those ending with "-start" or "-end".
    space_files = glob.glob("*.space")
    space_files = [f for f in space_files if not (f.endswith("-start.space") or f.endswith("-end.space"))]
    if not space_files:
        sys.stderr.write("Error: No valid savegame .space file found.\n")
        sys.exit(1)
    main_space_file = space_files[0]
    main_header, main_nodes = process_space_file(main_space_file)
    
    # Remove all content from the top-level "Missions" node (if it exists)
    for node in main_nodes:
        if node.tag and node.tag.lower() == "missions":
            node.attributes = []
            node.children = []
    
    # Remove existing friendly newship nodes only once from the source .space file.
    main_nodes = remove_newship_friendly(main_nodes)
    
    next_id_value = 1
    for k, v in main_header:
        if k.lower() == "nextid":
            try:
                next_id_value = int(v)
            except ValueError:
                next_id_value = 1
            break
    next_id = [next_id_value]
    
    # Initialize independent counters for Offset.y.
    friendly_count = 0
    hostile_count = 0
    
    # Dictionary to record ship file summary.
    ship_summary = {}
    
    ship_files = glob.glob("*.ship")
    if not ship_files:
        sys.stderr.write("Error: No .ship files found in the folder.\n")
        sys.exit(1)
    for ship_file in ship_files:
        layers = create_layers_for_ship(ship_file)
        ship_summary[os.path.basename(ship_file)] = len(layers)
        for layer in layers:
            update_ids(layer, next_id, inside_network=False)
            # Remove the entire workqueue node.
            remove_workqueue(layer)
            clear_crew_attributes(layer)
            # Remove all "Entities" attributes from all sub-nodes of any Habitation node.
            remove_entities_from_habitation(layer)
            faction = ""
            for k, v in layer.attributes:
                if k.lower() == "type":
                    faction = v
                    break
            if faction == "FriendlyShip":
                layer.attributes = set_attr(layer.attributes, "Offset.x", "0")
                layer.attributes = set_attr(layer.attributes, "Rotation", "0")
                offset_y = calc_offset(friendly_count)
                layer.attributes = set_attr(layer.attributes, "Offset.y", str(offset_y))
                friendly_count += 1
            elif faction == "HostileShip":
                layer.attributes = set_attr(layer.attributes, "Offset.x", "2000")
                layer.attributes = set_attr(layer.attributes, "Rotation", "180")
                offset_y = calc_offset(hostile_count)
                layer.attributes = set_attr(layer.attributes, "Offset.y", str(offset_y))
                hostile_count += 1
            update_shipai_layer_attribute(layer)
            main_nodes.append(layer)
            
            # For each appended ship, create or update the top-level "LayerOrders" node.
            new_id = None
            for key, value in layer.attributes:
                if key.lower() == "id":
                    new_id = value
                    break
            if new_id is not None:
                found = False
                for node in main_nodes:
                    if node.tag and node.tag.lower() == "layerorders":
                        for attr in node.attributes:
                            if attr[0].lower() == "id" and attr[1] == new_id:
                                node.attributes = set_attr(node.attributes, "Scope", "Layer")
                                node.attributes = set_attr(node.attributes, "Salvage", "false")
                                node.attributes = set_attr(node.attributes, "Gather", "false")
                                node.attributes = set_attr(node.attributes, "Mining", "false")
                                node.attributes = set_attr(node.attributes, "ExteriorWork", "false")
                                node.attributes = set_attr(node.attributes, "Id", new_id)
                                found = True
                                break
                    if found:
                        break
                if not found:
                    new_order = Node("LayerOrders")
                    new_order.attributes = []
                    new_order.attributes = set_attr(new_order.attributes, "Scope", "Layer")
                    new_order.attributes = set_attr(new_order.attributes, "Salvage", "false")
                    new_order.attributes = set_attr(new_order.attributes, "Gather", "false")
                    new_order.attributes = set_attr(new_order.attributes, "Mining", "false")
                    new_order.attributes = set_attr(new_order.attributes, "ExteriorWork", "false")
                    new_order.attributes = set_attr(new_order.attributes, "Id", new_id)
                    main_nodes.append(new_order)
    
    # Validate that at least one friendly and one hostile ship exist.
    if friendly_count < 1 or hostile_count < 1:
        sys.stderr.write("Error: At least one friendly and one hostile ship are required.\n")
        sys.exit(1)
    
    main_header = set_attr(main_header, "NextId", str(next_id[0]))
    # Set top level attributes TimeIndex and PlayTime to 0.
    main_header = set_attr(main_header, "TimeIndex", "0")
    main_header = set_attr(main_header, "PlayTime", "0")
    
    # Create or update the top-level "SystemOrders" node.
    system_found = False
    for node in main_nodes:
        if node.tag and node.tag.lower() == "systemorders":
            node.attributes = set_attr(node.attributes, "Id", "1")
            node.attributes = set_attr(node.attributes, "Scope", "System")
            node.attributes = set_attr(node.attributes, "FleetLogistics", "false")
            node.attributes = set_attr(node.attributes, "BattleStations", "true")
            system_found = True
            break
    if not system_found:
        system_node = Node("SystemOrders")
        system_node.attributes = []
        system_node.attributes = set_attr(system_node.attributes, "Id", "1")
        system_node.attributes = set_attr(system_node.attributes, "Scope", "System")
        system_node.attributes = set_attr(system_node.attributes, "FleetLogistics", "false")
        system_node.attributes = set_attr(system_node.attributes, "BattleStations", "true")
        main_nodes.append(system_node)
    
    base, ext = os.path.splitext(main_space_file)
    output_filepath = f"{base}-start{ext}"
    write_file(main_header, main_nodes, output_filepath)
    
    print("SUCCESS: Processed", len(ship_files), "ship file(s):")
    for ship_file, count in ship_summary.items():
        print(f"    {ship_file}: {count}")
    print(f"Output file: '{output_filepath}'")
    
if __name__ == "__main__":
    main()
