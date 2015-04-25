#!/usr/bin/env python3

import sql


def get_id(iri, entity_type="Class", _cache={}):
    if (iri, entity_type) in _cache:
        return _cache[iri, entity_type]
    
    with sql.lock:
        sql.cursor.execute(
            "SELECT id "
            "FROM owl_objects "
            "WHERE iri = %s AND type = %s "
            "LIMIT 1", (iri, entity_type))
        row = sql.cursor.fetchone()
    
    if row is None:
        result = get_next_id()
    else:
        result = row[0]
    
    _cache[iri, entity_type] = result
    return result


def seq_to_ids(seq, entity_type="Class"):
    t = type(seq)
    return t(get_id(iri, entity_type) for iri in seq)


NEXT_ID = None
def get_next_id():
    global NEXT_ID
    if NEXT_ID is None:
        with sql.lock:
            sql.cursor.execute("SELECT MAX(id) FROM owl_objects")
            NEXT_ID = sql.cursor.fetchone()[0] + 1
    else:
        NEXT_ID += 1
    
    return NEXT_ID


def model_to_seq(model):
    return {concept for annotations in model.values()
                    for concept in annotations}


def to_seq(obj):
    t = type(obj)
    if t in (tuple, list, set):
        return obj
    else:
        return [obj]
