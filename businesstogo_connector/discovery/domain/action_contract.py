"""Framework-independent, allowlisted JSON response contracts."""


def menu_id(value):
    if type(value) is not int or value <= 0:
        raise ValueError("menu_id must be a positive integer")
    return value


def action_descriptor(action):
    return {
        "id": action["id"],
        "type": "ir.actions.act_window",
        "name": action["name"],
        "res_model": action["res_model"],
        "res_id": action["res_id"] or False,
        "views": [list(view) for view in action["views"]],
        "domain": action["domain"],
        "context": action["context"],
        "search_view_id": action["search_view_id"][0] if action["search_view_id"] else False,
        "target": action["target"],
        "limit": action["limit"],
    }


def menu_descriptors(tree, allowed_action_ids):
    """Keep supported action menus and their reachable folder ancestors.

    Odoo owns the visibility-filtered, cached input tree. Never mutate it.
    allowed_action_ids contains menu IDs, not action IDs.
    """
    result = []

    def visit(node_id, parent_id):
        node = tree[node_id]
        children = []
        descendants = []
        for child_id in node["children"]:
            branch = visit(child_id, node_id)
            if branch:
                children.append(child_id)
                descendants.extend(branch)
        if node_id not in allowed_action_ids and not children:
            return []
        return [{
            "id": node_id,
            "name": node["name"],
            "parent_id": parent_id,
            "children": children,
            "has_action": node_id in allowed_action_ids,
        }, *descendants]

    for root_id in tree["root"]["children"]:
        result.extend(visit(root_id, False))
    return result
