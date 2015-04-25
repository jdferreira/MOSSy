import utils

from parse_config import register

@register()
class from_list_comparer:
    
    def __init__(self, inner):
        self.inner = inner
    
    
    def compare(self, one, two):
        return self.inner.compare(utils.model_to_seq(one),
                                  utils.model_to_seq(two))


@register()
class simple_model_comparer:
    
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



@register()
class model_min:
    
    def aggregate(self, similarities, one, two):
        return min(similarities.values())


@register()
class model_max:
    
    def aggregate(self, similarities, one, two):
        return max(similarities.values())


@register()
class model_avg:
    
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
