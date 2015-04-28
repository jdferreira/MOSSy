
from mossy import sql, utils

KNOWN_ENTITIES = [
    ("http://www.w3.org/2002/07/owl#Thing",             "Class"),
    ("http://www.example.org/mossy/test#Wolf",          "Class"),
    ("http://www.example.org/mossy/test#Rabbit",        "Class"),
    ("http://www.example.org/mossy/test#Swim",          "Class"),
    ("http://www.example.org/mossy/test#Water_habitat", "Class"),
    ("http://www.example.org/mossy/test#Apple_tree",    "Class"),
    ("http://www.example.org/mossy/test#Tongue",        "Class"),
    ("http://www.example.org/mossy/test#Carnivorous",   "Class"),
    ("http://www.example.org/mossy/test#Herbivorous",   "Class"),
    ("http://www.example.org/mossy/test#Mackarel",      "Class"),
    ("http://www.example.org/mossy/test#Whale",         "Class"),
    ("http://www.example.org/mossy/test#Shark",         "Class"),
    ("http://www.example.org/mossy/test#Flight",        "Class"),
    ("http://www.example.org/mossy/test#Tooth",         "Class"),
    ("http://www.example.org/mossy/test#Body_part",     "Class"),
    ("http://www.example.org/mossy/test#Squirrel",      "Class"),
    ("http://www.example.org/mossy/test#Mammal",        "Class"),
    ("http://www.example.org/mossy/test#Sparrow",       "Class"),
    ("http://www.example.org/mossy/test#Bird",          "Class"),
    ("http://www.example.org/mossy/test#Grass",         "Class"),
    ("http://www.example.org/mossy/test#Bat",           "Class"),
    ("http://www.example.org/mossy/test#Pine",          "Class"),
    ("http://www.example.org/mossy/test#Chicken",       "Class"),
    ("http://www.example.org/mossy/test#Fruit",         "Class"),
    ("http://www.example.org/mossy/test#Palm_tree",     "Class"),
    ("http://www.example.org/mossy/test#Salmon",        "Class"),
    ("http://www.example.org/mossy/test#Speed",         "Class"),
    ("http://www.example.org/mossy/test#Cow",           "Class"),
    ("http://www.example.org/mossy/test#Land",          "Class"),
    ("http://www.example.org/mossy/test#Eagle",         "Class"),
    ("http://www.example.org/mossy/test#Ostrich",       "Class"),
    ("http://www.example.org/mossy/test#Animal",        "Class"),
    ("http://www.example.org/mossy/test#Plant",         "Class"),
    ("http://www.example.org/mossy/test#Habitat",       "Class"),
    ("http://www.example.org/mossy/test#Tree",          "Class"),
    ("http://www.example.org/mossy/test#Mouth",         "Class"),
    ("http://www.example.org/mossy/test#Fish",          "Class"),
    ("http://www.example.org/mossy/test#Dog",           "Class"),
    ("http://www.example.org/mossy/test#Capability",    "Class"),
    ("http://www.example.org/mossy/test#Living_being",  "Class"),
    ("http://www.example.org/mossy/test#Walk",          "Class"),
    ("http://www.example.org/mossy/test#Penguin",       "Class"),
    ("http://www.example.org/mossy/test#Wing",          "Class"),
    ("http://www.example.org/mossy/test#eats",          "ObjectProperty"),
    ("http://www.example.org/mossy/test#hasHabitat",    "ObjectProperty"),
    ("http://www.example.org/mossy/test#hasPart",       "ObjectProperty"),
    ("http://www.example.org/mossy/test#hasCapability", "ObjectProperty"),
]

UNKNOWN_ENTITIES = [
    ("Class", "not an iri"),
    ("Class", "http://unknown"),
    ("Class", "http://www.example.org/mossy/test#Unknown_object"),
]

# Test that a connection to the database can be established
def test_make_connection():
    sql.set_connection("localhost", "owltosql", "owltosql", "owltosql")


def test_make_query():
    with sql.lock:
        sql.cursor.execute("SELECT COUNT(*) FROM owl_objects")
        return sql.cursor.fetchone()[0]

def test_utils_get_id():
    for iri, entity_type in KNOWN_ENTITIES + UNKNOWN_ENTITIES:
        entity_id = utils.get_id(iri, entity_type=entity_type)
        fetched_iri, fetched_type = utils.get_entity(entity_id)
        
        assert iri == fetched_iri and entity_type == fetched_type
    
    assert utils.get_entity(1000) == None
