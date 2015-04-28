import sys

from collections import defaultdict

from mossy import sql, utils
from mossy.parse_config import register
from mossy.plugins.concept_comparers import ICCalculator


def chain_to_ids(chain):
    properties = chain[:-1]
    concept = chain[-1]
    
    chain = [utils.get_id(i, "ObjectProperty") for i in properties]
    chain.append(utils.get_id(concept))
    
    return chain


def convert_input(item):
    # Each item can be one of the following:
    #   1. a concept
    #   2. a list of concepts
    #   3. a list of chains
    # where a chain is a sequence of properties followed by a concept:
    #   chain: [prop, prop, prop, ..., concept]
    # Concepts and properties are strings that represent their IRI
    # Any number of properties (including 0) is valid
    
    # Convert concepts to chains
    if type(item) == str:
        chains = [[item]]
    
    else:
        # Convert each concept in the list to a proper chain
        chains = [utils.to_seq(i) for i in item]
    
    # Finally, convert the properties and concepts to database indices
    chains = [chain_to_ids(i) for i in chains]
    
    return chains


@register()
class ferreira:
    
    def __init__(self, *,
                 ic=None,
                 distance_threshold=3,
                 weight_threshold=0.3,
                 property_weights=None,
                 default_weight=0.7,
                 hierarchy_weight=0.8,
                 discover_subclasses=False):
        
        self.distance_threshold = distance_threshold
        self.weight_threshold = weight_threshold
        self.default_weight = default_weight
        
        self.property_weights = {}
        if property_weights is not None:
            for prop, weight in property_weights.items():
                prop = utils.get_id(prop, "ObjectProperty")
                self.property_weights[prop] = weight
        
        # The class-subclass propertyis represented in this code
        # by the None object
        self.property_weights[None] = hierarchy_weight
        
        if ic:
            self.ic_calculator = ICCalculator(ic)
        else:
            self.ic_calculator = None
        
        self.get_relations_query = (
            "SELECT chain, end, distance "
            "FROM existential_relations "
            "WHERE start = %s AND distance <= %s")
        
        self.discover_subclasses = discover_subclasses
        if discover_subclasses:
            self.get_hierarchy_query = (
                "SELECT superclass "
                "FROM hierarchy "
                "WHERE subclass = %s AND distance = 1 "
                "UNION "
                "SELECT subclass "
                "FROM hierarchy "
                "WHERE superclass = %s AND distance = 1")
        else:
            self.get_hierarchy_query = (
                "SELECT superclass "
                "FROM hierarchy "
                "WHERE subclass = %s AND distance = 1")
    
    
    def compare(self, one, two):
        # Convert the input into actual chains of database indices
        one = convert_input(one)
        two = convert_input(two)
        
        n1 = self.construct_neighborhood(one)
        n2 = self.construct_neighborhood(two)
        
        return self.inter(n1, n2) / self.union(n1, n2)
    
    
    def inter(self, n1, n2):
        result = 0
        for concept_id, weight1 in n1.items():
            weight2 = n2.get(concept_id, 0)
            result += weight1 * weight2
        return result
    
    
    def union(self, n1, n2):
        result = 0
        concepts = set(n1).union(n2)
        for concept_id in concepts:
            weight1 = n1.get(concept_id, 0)
            weight2 = n2.get(concept_id, 0)
            result += weight1 + weight2 - weight1 * weight2
        return result
    
    
    def construct_neighborhood(self, chains):
        result = defaultdict(int)
        for chain in chains:
            neighbors = self.find_and_weigh_neighbors(chain)
            for concept_id, weight in neighbors.items():
                result[concept_id] = max(result[concept_id], weight)
        
        return result
    
    
    def find_and_weigh_neighbors(self, chain, ttt=None):
        """
        This method finds, for a given chain, a collection of more chains that
        are inferred from the given one. This is done by:
        
          1. replacing the concept with its named superclasses
          2. replacing the concept with its existential relations:
             ?A rdfs:subClassOf [
                  a owl:Restriction ;
                  owl:onProperty ?p ;
                  owl:someValuesFrom ?B ]
             In this case, concept ?A would be replaced by the chain (?p, ?B)
        
        The stop criteria are given by self.distance_threshold and
        self.weight_threshold
        """
        
        # For each step of the iteration below, we need to know:
        #   1. The id of the concept to expand
        #   2. The distance travelled to reach it
        #   3. The weight of the corresponding chain
        
        result = defaultdict(int)
        
        chain_weight = (self.get_properties_weight(chain[:-1]) *
                        self.get_ic(chain[-1]))
        
        # Each item in the todo list is a tuple:
        #   (concept_id, length to get here, weight of the chain to get here)
        # Once we reach a tuple that is beyond the thresholds for this comparer
        # we discard it.
        todo = [(chain[-1], len(chain) - 1, chain_weight)]
        
        while todo:
            concept_id, prev_distance, prev_weight = todo.pop()
            
            result[concept_id] = max(result[concept_id], prev_weight)
            
            max_distance = self.distance_threshold - prev_distance
            with sql.lock:
                sql.cursor.execute(self.get_relations_query,
                                   (concept_id, max_distance))
                for props, end, distance in sql.cursor:
                    props = [int(i) for i in props.split(',')]
                    current_weight = (prev_weight *
                                      self.get_properties_weight(props))
                    current_distance = prev_distance + distance
                    
                    if (current_distance <= self.distance_threshold
                            and current_weight >= self.weight_threshold):
                        todo.append((end, current_distance, current_weight))
        
                if not self.property_weights[None]:
                    continue
                
                if self.discover_subclasses:
                    args = (concept_id, concept_id)
                else:
                    args = (concept_id,)
                sql.cursor.execute(self.get_hierarchy_query, args)
                
                for relative, in sql.cursor:
                    current_distance = prev_distance + 1
                    current_weight = prev_weight * self.property_weights[None]
                    if (current_distance <= self.distance_threshold
                            and current_weight >= self.weight_threshold):
                        todo.append((relative,
                                    current_distance,
                                    current_weight))
        
        return result
                    
    
    
    def get_properties_weight(self, props):
        result = 1
        for prop in props:
            result *= self.property_weights.get(prop, self.default_weight)
        return result
    
    
    def get_ic(self, concept):
        if self.ic_calculator is None:
            return 1
        else:
            return self.ic_calculator.get(concept)
