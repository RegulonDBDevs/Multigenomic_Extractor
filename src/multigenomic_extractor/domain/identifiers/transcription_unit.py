"""Identifier identity for a predicted transcription unit."""


def transcription_unit(**document):
    return [document["organisms_id"], document["_id"]]
