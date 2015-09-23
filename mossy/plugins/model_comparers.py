from mossy import utils
from mossy.parse_config import plugin

@plugin()
class from_list_comparer:
    """
    Constructor:
        from_list_comparer(inner)
    where
        `ìnner` is a comparer that can compare one sequence of concepts with
            another sequence of concepts
    
    Usage:
        .compare(one, two)
    where
        `one` and `two` are models
    
    A model is a dictionary that associates a set of ontology names with
    annotations that are concpets extracted from those ontologies. A model is
    converted to a set by aggregating all the concept in the same set,
    irrespective of the ontology they come from.
    """
    
    def __init__(self, inner):
        self.inner = inner
    
    
    def compare(self, one, two):
        return self.inner.compare(utils.model_to_seq(one),
                                  utils.model_to_seq(two))


@plugin()
class simple_model_comparer:
    """
    Constructor:
        simple_model_comparer(inners, aggr)
    where
        `ìnners` is a dictionary that associates ontology names with list
            comparers
        `aggr` is an object that contains the .aggregate method. Common values
            include the plugins `model_min`, `model_max` and `model_avg`.
    
    Usage:
        .compare(one, two)
    where
        `one` and `two` are models
    
    A model is a dictionary that associates a set of ontology names with
    annotations that are concpets extracted from those ontologies. This comparer
    compares all concepts from the model `one` and ontology `A` with all
    concepts from the model `two` and ontology `A`, for every òntology `A` and
    constructs a dictionary that associates each ontology name with a value.
    Then comparer then aggregates this dictionary using the `aggr` object.
    
    See also: `model_min`, `model_max`, `model_avg`
    """
    
    def __init__(self, inners, aggr):
        self.inners = inners
        self.aggr = aggr
    
    
    def compare(self, one, two):
        similarities = {}
        
        for key, inner in self.inners.items():
            first = one.get(key, [])
            second = two.get(key, [])
            
            if first and second:
                similarities[key] = inner.compare(first, second)
        
        
        if not similarities:
            return 0
        
        return self.aggr.aggregate(similarities, one, two)



@plugin()
class model_min:
    """
    Constructor:
        model_min()
    
    This object is used by the simple_model_comparer to aggregate the various
    similarity values obtained for each ontology and returns the minimum of all
    those similarity values
    """
    
    def aggregate(self, similarities, one, two):
        return min(similarities.values())


@plugin()
class model_max:
    """
    Constructor:
        model_max()
    
    This object is used by the simple_model_comparer to aggregate the various
    similarity values obtained for each ontology and returns the maximum of all
    those similarity values
    """
    
    def aggregate(self, similarities, one, two):
        return max(similarities.values())


@plugin()
class model_avg:
    """
    Constructor:
        model_min(weights=None)
    where
        `weights` is a dictionary of the weight of each ontology
    
    This object is used by the simple_model_comparer to aggregate the various
    similarity values obtained for each ontology and returns the average of
    those similarity values. You can specify weight values for each ontology
    as a dictioanry that associates ontology names with their weights. The
    weights can be integers or float values.
    
    Alteratively, weights can be set to the string "proportional", in which
    the weight of each ontology is set as the number of distinct annotations
    for that ontology in both models.
    """
    
    def __init__(self, weights=None):
        self.weights = weights
    
    
    def aggregate(self, similarities, one, two):
        if self.weights is None:
            # Return the non weighted average of the similarities
            return sum(similarities.values()) / len(similarities)
        
        num = den = 0
        
        if self.weights == "proportional":
            for key, partial in similarities.items():
                weight = len(set(one[key]).union(two[key]))
                num += weight * partial
                den += weight
            return num / den
        
        for key, weight in self.weights.items():
            if key not in similarities:
                continue
            
            num += weight * similarities[key]
            den += weight
        
        return num / den
