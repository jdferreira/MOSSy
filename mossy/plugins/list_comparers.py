from mossy.parse_config import plugin

@plugin()
class simple_list_comparer:
    """
    Constructor:
        simple_list_comparer(inner, aggr)
    where
        `inner` is a concept comparer (a comparer that can compare one concept
            to another)
        `aggr` is an object that contains the .aggregate method. Common values
            include the plugins `list_min`, `list_max`, `list_avg`, `list_bma`
            and `list_hna`.
    
    Usage:
        .compare(one, two)
    where
        `one` and `two` are concept sequences
    
    Each concept in `one` is compared to each concept in `two`, producing a
    matrix of similarity values. This comparer uses a specified strategy to
    aggregate the matrix into a single value.
    
    See also: `list_min`, `list_max`, `list_avg`, `list_bma`, `list_hna`
    """
    
    def __init__(self, inner, aggr):
        self.inner = inner
        self.aggr = aggr
    
    
    def compare(self, one, two):
        matrix = []
        for first in one:
            row = []
            for second in two:
                sim = self.inner.compare(first, second)
                row.append(sim)
            matrix.append(row)
        
        if not matrix or not matrix[0]:
            if hasattr(self.inner, 'void'):
                # If the inner comparer defines the value that should be given
                # to the comparison between entities one of which is void, use
                # that value
                return self.inner.void
            else:
                return 0
        
        return self.aggr.aggregate(matrix, one, two)


@plugin()
class list_min:
    """
    Constructor:
        list_min()
    
    This object is used by the simple_list_comparer to aggregate the similarity
    matrix values and returns the minimum of all those values
    """
    
    def aggregate(self, matrix, one, two):
        return min(value for row in matrix for value in row)


@plugin()
class list_max:
    """
    Constructor:
        list_max()
    
    This object is used by the simple_list_comparer to aggregate the similarity
    matrix values and returns the maximum of all those values
    """
    
    def aggregate(self, matrix, one, two):
        return max(value for row in matrix for value in row)


@plugin()
class list_avg:
    """
    Constructor:
        list_avg()
    
    This object is used by the simple_list_comparer to aggregate the similarity
    matrix values and returns the average of all those values
    """
    
    def aggregate(self, matrix, one, two):
        total = sum(value for row in matrix for value in row)
        count = sum(1 for row in matrix for value in row)
        return total / count


@plugin()
class list_bma:
    """
    Constructor:
        list_min()
    
    This object is used by the simple_list_comparer to aggregate the similarity
    matrix values. It first finds the maximum value in each row and the maximum
    value in each column, and then averages all these `n + m` values (where `n`
    is the number of rows and `m` is the number of columns)
    """
    
    def aggregate(self, matrix, one, two):
        max_rows = [max(row) for row in matrix]
        max_cols = [0 for i in matrix[0]]
        for row in matrix:
            for col_no, value in enumerate(row):
                max_cols[col_no] = max(max_cols[col_no], value)
        
        return (sum(max_rows) + sum(max_cols)) / (len(max_rows) + len(max_cols))


@plugin()
class list_hna:
    """
    Constructor:
        list_min(n=10, mode='highest')
    where
        `n` defines how many values to consider
        `mode` defines whether to consider the 'highest' of the 'lowest' values
    
    This object is used by the simple_list_comparer to aggregate the similarity
    matrix values. It finds the maximum `n` values of the matrix and returns
    their average (or the minimum `n`, in case `mode == 'lowest'`).
    """
    
    def __init__(self, n=10, mode="highest"):
        if mode not in ("highest", "lowest"):
            raise ValueError("Valid modes are 'highest' and 'lowest'")
        
        self.n = n
        self.mode = mode
    
    
    def aggregate(self, matrix, one, two):
        flat = sorted(value for row in matrix for value in row)
        n = min(self.n, len(flat))
        if self.mode == "highest":
            flat = flat[-n:]
        else:
            flat = flat[:n]
        return sum(flat) / self.n
