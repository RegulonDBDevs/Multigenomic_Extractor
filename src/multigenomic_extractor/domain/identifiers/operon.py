"""Identifier identity for a predicted operon (stable across reruns)."""


def operon(**document):
    return [
        document["organisms_id"],
        document["regulationPositions"],
        document["strand"],
        document["name"],
    ]
