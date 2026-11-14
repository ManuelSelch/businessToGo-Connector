import hashlib
import json


def positive_id(value):
    if type(value) is not int or value <= 0:
        raise ValueError("A positive receipt ID is required.")
    return value


def revision(snapshot):
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True, default=str).encode()).hexdigest()


def counts(lines, quantities):
    if not isinstance(quantities, list) or len(quantities) != len(lines):
        raise ValueError("Every receipt line must be supplied exactly once.")
    expected = {line["id"]: line["expected"] for line in lines}
    result = {}
    for entry in quantities:
        if not isinstance(entry, dict) or set(entry) != {"id", "quantity"}:
            raise ValueError("Invalid quantity entry.")
        key, value = entry["id"], entry["quantity"]
        if type(key) is not int or key not in expected or key in result:
            raise ValueError("Unknown or repeated receipt line.")
        if type(value) is not int or not 0 <= value <= expected[key]:
            raise ValueError("Only whole counts from zero to demand are supported.")
        result[key] = value
    return result
