from mossy import utils
from mossy.parse_config import plugin

@plugin()
class integrative_comparer:
    """
    Constructor:
        integrative_comparer(inner)
    where
        `ìnner` is a comparer that can compare one sequence of concepts with
            another sequence of concepts
    
    Usage:
        .compare(one, two)
    where
        `one` and `two` are models
    
    A model is a dictionary that associates a set of domain names with
    annotations that are concpets extracted from those domains. A model is
    converted to a list of annotations by combining together the concept in one
    set, irrespective of the domain they come from.
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
        `ìnners` is a dictionary that associates domain names with list
            comparers
        `aggr` is an object that contains the .aggregate method. Common values
            include the plugins `model_min`, `model_max` and `model_avg`.
    
    Usage:
        .compare(one, two)
    where
        `one` and `two` are models
    
    A model is a dictionary that associates a set of domain names with
    annotations that are concpets extracted from those domains. This comparer
    compares all concepts from the model `one` and domain `A` with all
    concepts from the model `two` and domain `A`, for every òntology `A` and
    constructs a dictionary that associates each domain name with a value.
    The comparer then aggregates this dictionary using the `aggr` object.
    
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
class aggregative_comparer:
    """
    Constructor:
        aggregative_comparer(inner, aggr, only=[])
    where
        `ìnner` is a comparer to compare cocnepts within each domain
        `aggr` is an object that contains the .aggregate method. Common values
            include the plugins `model_min`, `model_max` and `model_avg`.
        `only` is a list of domain names. If provided, only those domains are
            used to compare the models; otherwise, all common domains are used
    
    Usage:
        .compare(one, two)
    where
        `one` and `two` are models
    
    A model is a dictionary that associates a set of domain names with a list
    of annotations (concepts from those domains). This comparer compares all
    concepts from the model `one` and domain `A` with all concepts from the
    model `two` and domain `A`, for every domain `A` and constructs a dictionary
    that associates each domain name with a value. Then, the comparer aggregates
    this dictionary using the `aggr` object.
    
    See also: `model_min`, `model_max`, `model_avg`
    """
    
    def __init__(self, inner, aggr, only=None):
        self.inner = inner
        self.aggr = aggr
        self.only = only
    
    
    def compare(self, one, two):
        similarities = {}
        
        # Get the list of domains to consider (the intersection of them)
        domains = set(one).intersection(two)
        if self.domains is not None:
            domains.intersection_update(self.only)
        
        if not domains:
            return 0
        
        for domain in domains:
            first = one[domain]
            second = two[domain]
            similarities[domain] = self.inner.compare(first, second)
        
        return self.aggr.aggregate(similarities, one, two)


@plugin()
class model_min:
    """
    Constructor:
        model_min()
    
    This object is used by the simple_model_comparer to aggregate the various
    similarity values obtained for each domain and returns the minimum of all
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
    similarity values obtained for each domain and returns the maximum of all
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
        `weights` is a dictionary of the weight of each domain
    
    This object is used by the simple_model_comparer to aggregate the various
    similarity values obtained for each domain and returns the average of
    those similarity values. You can specify weight values for each domain
    as a dictioanry that associates domain names with their weights. The
    weights can be integers or float values.
    
    Alteratively, weights can be set to the string "proportional", in which
    the weight of each domain is set as the number of distinct annotations
    for that domain in both models.
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
