from mossy import sql, utils
from mossy.parse_config import plugin


@plugin()
class subsumption:
    """
    Constructor:
        subsumption(inner, hierarchy)
    where
        `ìnner` is a comparer that can compare one concept with another concept
        `hierarchy` is the name of a hierarchy (a table in the underlying SQL
            database) which defines the hierarchy to use when determining
            whether a concept is a superclass of another concept
    
    Usage:
        .compare(one, two)
    where
        `one` is a concept
        `two` is a sequence of concepts.
    
    Returns returns 1 if any of the concepts in `two` is a superclass of `one`.
    Otherwise, compare the concept `one` with all concepts in `two` using the
    `inner` comparer, supplied at construction time, and return the maximum of
    those values.
    """
    
    def __init__(self, inner, hierarchy=None):
        
        self.inner = inner
        
        if hierarchy is None:
            self.get_super_query = (
                "SELECT superclass "
                "FROM hierarchy "
                "WHERE subclass = %s")
            self.two_args = False
        
        else:
            self.get_super_query = (
                "SELECT superclass "
                "FROM hierarchy "
                "WHERE subclass = %s "
                "UNION "
                "SELECT superclass "
                "FROM extended_hierarchy "
                "WHERE extension = '{}' AND subclass = %s ".format(hierarchy))
            self.two_args = True
    
    
    def compare(self, one, two):
        one = utils.get_id(one)
        two = utils.seq_to_ids(two)
        
        with sql.lock:
            if not self.two_args:
                args = (one,)
            else:
                args = (one, one)
            sql.cursor.execute(self.get_super_query, args)
            superclasses = {i[0] for i in sql.cursor}
        
        # If one of the concepts in the second argument is superclass of the
        # first argument, return 1
        if any(i in two for i in superclasses):
            return 1
        
        # Otherwise, compare the concept with any of the concepts of the second
        # list and return the maximum similarity value found
        result = 0
        for second in two:
            result = max(result, self.inner.compare(one, second))
        return result;
