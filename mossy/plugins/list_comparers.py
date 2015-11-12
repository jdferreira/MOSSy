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
    
    This object is used by the `simple_list_comparer` to aggregate the
    similarity matrix values and returns the minimum of all those values
    """
    
    def aggregate(self, matrix, one, two):
        return min(value for row in matrix for value in row)


@plugin()
class list_max:
    """
    Constructor:
        list_max()
    
    This object is used by the `simple_list_comparer` to aggregate the
    similarity matrix values and returns the maximum of all those values
    """
    
    def aggregate(self, matrix, one, two):
        return max(value for row in matrix for value in row)


@plugin()
class list_avg:
    """
    Constructor:
        list_avg()
    
    This object is used by the `simple_list_comparer` to aggregate the
    similarity matrix values and returns the average of all those values
    """
    
    def aggregate(self, matrix, one, two):
        total = sum(value for row in matrix for value in row)
        count = sum(1 for row in matrix for value in row)
        return total / count


@plugin()
class list_bma:
    """
    Constructor:
        list_bma(best_match="max")
    where:
        `best_match` is either "max" or "min" and defines what constitutes a
            best match. If "max", the maximum of each row and column are used;
            if "min" the minimum of each row and column are used.
    
    This object is used by the `simple_list_comparer` to aggregate the
    similarity matrix values. It first finds the maximum value in each row and
    the maximum value in each column, and then takes the average of these
    `n + m` values (where `n` is the number of rows and `m` is the number of
    columns). If `best_match` is "min", replace "maximum" with "minimum" in this
    paragraph.
    """
    
    def __init__(self, best_match="max"):
        if best_match == "max":
            self.best_match = max
        elif best_match == "min":
            self.best_match = min
        else:
            raise ValueError(
                "Valid values for `best_match` are 'max' and 'min'.")
    
    
    def aggregate(self, matrix, one, two):
        max_rows = [max(row) for row in matrix]
        
        max_cols = [0 for i in matrix[0]]
        for row in matrix:
            for col_no, value in enumerate(row):
                max_cols[col_no] = self.best_match(max_cols[col_no], value)
        
        num = sum(max_rows) + sum(max_cols)
        den = len(max_rows) + len(max_cols)
        return num / den


@plugin()
class list_hna:
    """
    Constructor:
        list_hna(n=10, mode='highest')
    where
        `n` defines how many values to consider. If the value is greater 1 or
            more, we use that amount of values; if the number is between 0 and
            1, we use interpret it as a fraction of all values in the matrix
        `mode` defines whether to consider the 'highest' of the 'lowest' values
    
    This object is used by the `simple_list_comparer` to aggregate the
    similarity matrix values. It finds the maximum `n` values of the matrix and
    returns their average (or the minimum `n`, in case `mode == 'lowest'`).
    """
    
    def __init__(self, n=10, mode="highest"):
        if mode not in ("highest", "lowest"):
            raise ValueError("Valid modes are 'highest' and 'lowest'")
        
        self.n = n
        self.mode = mode
    
    
    def aggregate(self, matrix, one, two):
        flat = sorted(value for row in matrix for value in row)
        
        if self.n < 1:
            n = self.n * len(flat)
        else:
            n = min(self.n, len(flat))
        
        if self.mode == "highest":
            highest = flat[-n:]
        else:
            highest = flat[:n]
        
        return sum(highest) / len(highest)
