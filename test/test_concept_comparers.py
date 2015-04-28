
import mossy.plugins.concept_comparers as plugin

from mossy import sql, utils

sql.set_connection("localhost", "owltosql", "owltosql", "owltosql")

BASE_IRI = "http://www.example.org/mossy/test#"

EPSILON = 1e-8
IC_NAMES = ("seco", "zhou", "sanchez", "leaves")
IC_TESTS = {
    BASE_IRI + "Animal":         (0.19054494733736993, 0.43657557091167765,  0.2501619701907851, 0.20379504709050622),
    BASE_IRI + "Apple_tree":     (                  1,                   1,    0.69957514867698,                   1),
    BASE_IRI + "Bat":            (                  1,                   1,    0.69957514867698,                   1),
    BASE_IRI + "Bird":           ( 0.5236202770089367,  0.6924866965778613, 0.44371369105404296,  0.5268025545616607),
    BASE_IRI + "Body_part":      ( 0.5236202770089367,  0.4771484175411649,   0.346937830622414,  0.5268025545616607),
    BASE_IRI + "Capability":     ( 0.5720945807380097,  0.5013855694057013, 0.37809269900225356,  0.5924099058189877),
    BASE_IRI + "Carnivorous":    ( 0.6314223337025877,  0.7463877249246869,  0.5150341705379842,  0.6769924925288455),
    BASE_IRI + "Chicken":        (                  1,                   1,  0.7250305296246676,                   1),
    BASE_IRI + "Cow":            (                  1,                   1,    0.69957514867698,                   1),
    BASE_IRI + "Dog":            (                  1,                   1,    0.69957514867698,                   1),
    BASE_IRI + "Eagle":          (                  1,                   1,  0.7250305296246676,                   1),
    BASE_IRI + "Fish":           ( 0.6314223337025877,  0.7463877249246869,  0.5150341705379842,  0.6769924925288455),
    BASE_IRI + "Flight":         (                  1,  0.8413030972429927,  0.6282546691930387,                   1),
    BASE_IRI + "Fruit":          (                  1,  0.8413030972429927,  0.6282546691930387,                   1),
    BASE_IRI + "Grass":          (                  1,  0.9306765580733931,  0.6684202802971404,                   1),
    BASE_IRI + "Habitat":        ( 0.7079091101576427,  0.5692928341155179,  0.4748685594338825,  0.7962049529094939),
    BASE_IRI + "Herbivorous":    ( 0.5720945807380097,  0.7167238484423979,  0.4748685594338825,  0.5924099058189877),
    BASE_IRI + "Land":           (                  1,  0.8413030972429927,  0.6282546691930387,                   1),
    BASE_IRI + "Living_being":   (0.11405817088231485,  0.2723673644778539,  0.1605475797008185,  0.1342934123607077),
    BASE_IRI + "Mackarel":       (                  1,                   1,    0.69957514867698,                   1),
    BASE_IRI + "Mammal":         (0.44713350055388146,  0.6542433083503338,  0.3967360921780472, 0.42787497145950626),
    BASE_IRI + "Mouth":          (                  1,  0.8413030972429927,  0.6282546691930387,                   1),
    BASE_IRI + "Ostrich":        (                  1,                   1,  0.7250305296246676,                   1),
    BASE_IRI + "Palm_tree":      (                  1,                   1,    0.69957514867698,                   1),
    BASE_IRI + "Penguin":        (                  1,                   1,  0.7250305296246676,                   1),
    BASE_IRI + "Pine":           (                  1,                   1,    0.69957514867698,                   1),
    BASE_IRI + "Plant":          ( 0.5236202770089367,   0.603113235747461, 0.43470294832978085,  0.5924099058189877),
    BASE_IRI + "Rabbit":         (                  1,                   1,  0.7250305296246676,                   1),
    BASE_IRI + "Salmon":         (                  1,                   1,    0.69957514867698,                   1),
    BASE_IRI + "Shark":          (                  1,                   1,  0.7250305296246676,                   1),
    BASE_IRI + "Sparrow":        (                  1,                   1,    0.69957514867698,                   1),
    BASE_IRI + "Speed":          (                  1,  0.8413030972429927,  0.6282546691930387,                   1),
    BASE_IRI + "Squirrel":       (                  1,                   1,  0.7250305296246676,                   1),
    BASE_IRI + "Swim":           (                  1,  0.8413030972429927,  0.6282546691930387,                   1),
    BASE_IRI + "Tongue":         (                  1,  0.8413030972429927,  0.6282546691930387,                   1),
    BASE_IRI + "Tooth":          (                  1,  0.8413030972429927,  0.6282546691930387,                   1),
    BASE_IRI + "Tree":           ( 0.6314223337025877,  0.7463877249246869,  0.5150341705379842,  0.6769924925288455),
    BASE_IRI + "Walk":           (                  1,  0.8413030972429927,  0.6282546691930387,                   1),
    BASE_IRI + "Water_habitat":  (                  1,  0.8413030972429927,  0.6282546691930387,                   1),
    BASE_IRI + "Whale":          (                  1,                   1,    0.69957514867698,                   1),
    BASE_IRI + "Wing":           (                  1,  0.8413030972429927,  0.6282546691930387,                   1),
    BASE_IRI + "Wolf":           (                  1,                   1,    0.69957514867698,                   1),
    "http://www.w3.org/2002/07/owl#Thing":              (                  0,                   0,                   0,                   0)
}

DISJOINT_FACTOR_RESULTS = [
    
    ("http://www.example.org/mossy/test#Shark",
     "http://www.example.org/mossy/test#Penguin",
     0.5),
    
    ("http://www.example.org/mossy/test#Shark",
     "http://www.example.org/mossy/test#Eagle",
     0.5),
    
    ("http://www.example.org/mossy/test#Shark",
     "http://www.example.org/mossy/test#Sparrow",
     0.5),
    
    ("http://www.example.org/mossy/test#Carnivorous",
     "http://www.example.org/mossy/test#Herbivorous",
     0),
    
    ("http://www.example.org/mossy/test#Bird",
     "http://www.example.org/mossy/test#Mammal",
     0.5),
    
    ("http://www.example.org/mossy/test#Bird",
     "http://www.example.org/mossy/test#Tree",
     0.5),
    
    ("http://www.example.org/mossy/test#Swim",
     "http://www.example.org/mossy/test#Flight",
     0.5),
    
    ("http://www.example.org/mossy/test#Tree",
     "http://www.example.org/mossy/test#Fruit",
     0.25),
]


SHARED_IC_RESULTS = [
    ("http://www.example.org/mossy/test#Shark",
     "http://www.example.org/mossy/test#Penguin",
     "http://www.example.org/mossy/test#Carnivorous",
     "http://www.example.org/mossy/test#Animal"),
    
    ("http://www.example.org/mossy/test#Shark",
     "http://www.example.org/mossy/test#Eagle",
     "http://www.example.org/mossy/test#Carnivorous",
     "http://www.example.org/mossy/test#Animal"),
    
    ("http://www.example.org/mossy/test#Shark",
     "http://www.example.org/mossy/test#Sparrow",
     "http://www.example.org/mossy/test#Animal",
     "http://www.example.org/mossy/test#Living_being"),
    
    ("http://www.example.org/mossy/test#Carnivorous",
     "http://www.example.org/mossy/test#Herbivorous",
     "http://www.example.org/mossy/test#Animal",
     "http://www.example.org/mossy/test#Living_being"),
    
    ("http://www.example.org/mossy/test#Bird",
     "http://www.example.org/mossy/test#Mammal",
     "http://www.example.org/mossy/test#Animal",
     "http://www.example.org/mossy/test#Living_being"),
    
    ("http://www.example.org/mossy/test#Bird",
     "http://www.example.org/mossy/test#Tree",
     "http://www.example.org/mossy/test#Living_being",
     "http://www.w3.org/2002/07/owl#Thing"),
    
    ("http://www.example.org/mossy/test#Swim",
     "http://www.example.org/mossy/test#Flight",
     "http://www.example.org/mossy/test#Capability",
     "http://www.w3.org/2002/07/owl#Thing"),
    
    ("http://www.example.org/mossy/test#Tree",
     "http://www.example.org/mossy/test#Fruit",
     "http://www.w3.org/2002/07/owl#Thing",
     None),
]

class TestICFunctions:
    
    def test_singleton(self):
        for ic in IC_NAMES:
            tmp1 = plugin.ICCalculator(ic)
            tmp2 = plugin.ICCalculator(ic)
            assert tmp1 is tmp2
    
    
    def test_ic_values(self):
        for index, ic_name in enumerate(IC_NAMES):
            ic_calculator = plugin.ICCalculator(ic_name)
            for iri, values in IC_TESTS.items():
                concept_id = utils.get_id(iri)
                ic = ic_calculator.get(concept_id)
                expected = values[index]
                print(iri, ic, expected)
                assert abs(ic - expected) < EPSILON
    
    
    def test_disjoint_factor(self):
        df = plugin.DisjointFactor()
        for one, two, result in DISJOINT_FACTOR_RESULTS:
            one_id = utils.get_id(one)
            two_id = utils.get_id(two)
            assert abs(df.get(one_id, two_id) - result) < EPSILON
    
    
    def test_shared_ic(self):
        df = plugin.DisjointFactor()
        for ic in IC_NAMES:
            ic_calculator = plugin.ICCalculator(ic)
            shared_ic_calculator_no_disjoints = \
                plugin.SharedICCalculator(ic, use_disjoints=False)
            shared_ic_calculator_disjoints = \
                plugin.SharedICCalculator(ic, use_disjoints=True)
            
            for one, two, mica, z in SHARED_IC_RESULTS:
                one_id = utils.get_id(one)
                two_id = utils.get_id(two)
                
                mica_id = utils.get_id(mica)
                ic_mica = ic_calculator.get(mica_id)
                
                result = shared_ic_calculator_no_disjoints.get(one_id, two_id)
                assert abs(result - ic_mica) < EPSILON
                
                if z is None:
                    expected = 0
                else:
                    z_id = utils.get_id(z)
                    ic_z = ic_calculator.get(z_id)
                    
                    factor = df.get(one_id, two_id)
                    expected = ic_mica - factor * (ic_mica - ic_z)
                
                result = shared_ic_calculator_disjoints.get(one_id, two_id)
                
                assert abs(result - expected) < EPSILON

