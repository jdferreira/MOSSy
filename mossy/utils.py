#!/usr/bin/env python3

from mossy import sql


ENTITY_CACHE = {}
ID_CACHE = {}

def get_id(iri, entity_type="Class"):
    if (iri, entity_type) in ENTITY_CACHE:
        return ENTITY_CACHE[iri, entity_type]
    
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
    
    ENTITY_CACHE[iri, entity_type] = result
    ID_CACHE[result] = (iri, entity_type)
    return result


def get_entity(entity_id):
    if entity_id in ID_CACHE:
        return ID_CACHE[entity_id]
    
    with sql.lock:
        sql.cursor.execute(
            "SELECT iri, type "
            "FROM owl_objects "
            "WHERE id = %s "
            "LIMIT 1", (entity_id,))
        row = sql.cursor.fetchone()
    
    if row is None:
        return None
    
    ID_CACHE[entity_id] = row
    ENTITY_CACHE[row] = entity_id
    return row
    


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
    if isinstance(obj, (tuple, list, set)):
        return obj
    else:
        return [obj]

