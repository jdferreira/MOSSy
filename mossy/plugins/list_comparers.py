from parse_config import register

@register()
class simple_list_comparer:
    
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


PLUS_INF = float('inf')
MINUS_INF = -PLUS_INF

@register()
class list_min:
    
    def aggregate(self, matrix, one, two):
        return min(value for row in matrix for value in row)


@register()
class list_max:
    
    def aggregate(self, matrix, one, two):
        return max(value for row in matrix for value in row)


@register()
class list_avg:
    
    def aggregate(self, matrix, one, two):
        total = sum(value for row in matrix for value in row)
        count = sum(1 for row in matrix for value in row)
        return total / count


@register()
class list_bma:
    
    def aggregate(self, matrix, one, two):
        max_rows = [max(row) for row in matrix]
        max_cols = [0 for i in matrix[0]]
        for row in matrix:
            for col_no, value in enumerate(row):
                max_cols[col_no] = max(max_cols[col_no], value)
        
        return (sum(max_rows) + sum(max_cols)) / (len(max_rows) + len(max_cols))


@register()
class list_hna:
    
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
