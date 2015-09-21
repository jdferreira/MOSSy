from mossy import sql, utils
from mossy.parse_config import plugin


def table_column_from_ic(ic):
    sql.assert_identifier(ic)
    
    if ic != "extrinsic":
        table = "intrinsic_ic"
        column = ic
    else:
        table = "extrinsic_ic"
        column = "ic"
    
    return table, column


class ArgSingleton(type):
    
    __instances = {}
    
    def __call__(cls, *args):
        if (cls, args) in ArgSingleton.__instances:
            return ArgSingleton.__instances[cls, args]
        
        result = super().__call__(*args)
        ArgSingleton.__instances[cls, args] = result
        return result


class ICCalculator(metaclass=ArgSingleton):
    
    def __init__(self, ic):
        table, column = table_column_from_ic(ic)
        self.get_ic_query = ("SELECT {} FROM {} WHERE id = %s"
                             .format(column, table))
        self._cache = {}
    
    
    def get(self, concept):
        if concept in self._cache:
            return self._cache[concept]
        
        with sql.lock:
            sql.cursor.execute(self.get_ic_query, (concept,))
            row = sql.cursor.fetchone()
        
        if row is None:
            result = -1
        else:
            result = row[0]
        
        self._cache[concept] = result
        return result


class DisjointFactor:
    
    def __init__(self):
        
        # This is a very big and complex SQL statement. It works as detailed in
        # the paper
        self.get_distance_query = (
            "SELECT MIN(h1.distance + h2.distance) "
            "FROM (SELECT h1.superclass AS super1, h2.superclass AS super2 "
            "      FROM hierarchy AS h1, hierarchy AS h2, disjoints "
            "      WHERE h1.subclass = %s AND h2.subclass = %s AND "
            "            disjoints.id1 = h1.superclass AND "
            "            disjoints.id2 = h2.superclass "
            "      UNION "
            "      SELECT h1.superclass AS super1, h2.superclass AS super2 "
            "      FROM hierarchy AS h1, hierarchy AS h2, disjoints "
            "      WHERE h1.subclass = %s AND h2.subclass = %s AND "
            "            disjoints.id1 = h2.superclass AND "
            "            disjoints.id2 = h1.superclass"
            "     ) AS t, "
            "     hierarchy AS h1, "
            "     hierarchy AS h2 "
            "WHERE h1.subclass = t.super1 AND "
            "      h2.subclass = t.super2 AND "
            "      h1.superclass = h2.superclass")
    
    
    def get(self, one, two):
        with sql.lock:
            sql.cursor.execute(self.get_distance_query, (one, two, one, two))
            factor = sql.cursor.fetchone()[0]
        
        if factor is None:
            return 0
        else:
            factor = 1 / factor
        
        return factor


class SharedICCalculator:
    
    def __init__(self, ic, hierarchy=None, use_disjoints=None):
        table, column = table_column_from_ic(ic)
        
        if use_disjoints and hierarchy is not None:
            raise Exception("Cannot calcualte shared IC using both "
                            "disjoint information and a custom hierarchy.");
        
        self.z_query = (
            "SELECT MAX(t.{}) "
            "FROM hierarchy "
            "JOIN {} AS t ON t.id = hierarchy.superclass "
            "WHERE hierarchy.distance = 1 AND "
            "      hierarchy.subclass = %s".format(column, table))
        
        self.get_mica_query = (
            "SELECT t.id "
            "FROM hierarchy AS h1, hierarchy AS h2, {} AS t "
            "WHERE h1.subclass = %s AND "
            "      h2.subclass = %s AND "
            "      h1.superclass = h2.superclass AND "
            "      t.id = h1.superclass "
            "ORDER BY {} DESC LIMIT 1".format(table, column))
        
        if hierarchy is None:
            self.get_xhierarchy_query = False
        else:
            self.get_xhierarchy_query = (
                "SELECT t.id "
                "FROM extended_hierarchy AS e1, "
                "     extended_hierarchy AS e2, "
                "     {table} AS t "
                "WHERE e1.subclass = %s AND "
                "      e2.subclass = %s AND "
                "      e1.superclass = e2.superclass AND "
                "      t.id = e1.superclass AND "
                "      e1.extension = {hierarchy} AND "
                "      e2.extension = {hierarchy} "
                "ORDER BY ic DESC LIMIT 1"
                .format(table=table, hierarchy=sql.conn.escape(hierarchy)))
        
        if not use_disjoints:
            self.use_disjoints = False
        else:
            self.use_disjoints = DisjointFactor()
        
        self.ic_calculator = ICCalculator(ic)
    
    
    def get(self, one, two):
        # Note: If there is an extension hierarchy from a property that is
        # reflexive, this first part is irrelevant, as the same result will by
        # definition be obtained by querying only the extended hierarchy ...
        # This, however, can not be determined by looking into the database
        # alone. Maybe we should create a table that stores whether a given
        # extension is transitive and/or reflexive
        
        with sql.lock:
            sql.cursor.execute(self.get_mica_query, (one, two))
            row = sql.cursor.fetchone()
        
        if row is None:
            return 0
    
        mica = row[0]
        ic_mica = self.ic_calculator.get(mica)
        
        if self.get_xhierarchy_query:
            with sql.lock:
                sql.cursor.execute(self.get_xhierarchy_query, (one, two))
                row = sql.cursor.fetchone()
            
            if row is not None:
                tmp_mica = row[0]
                ic_tmp_mica = self.ic_calculator.get(tmp_mica)
                if ic_tmp_mica > ic:
                    mica, ic_mica = tmp_mica, ic_tmp_mica
        
        # Note: Can we in any way use the extended hierarchy with the
        # disjointness theory?
        if not self.use_disjoints:
            return ic_mica
        
        factor = self.use_disjoints.get(one, two)
        
        # Find most informative ancestor of MICA
        with sql.lock:
            sql.cursor.execute(self.z_query, (mica,))
            ic_z = sql.cursor.fetchone()[0] or 0
        
        return ic_mica - factor * (ic_mica - ic_z)


@plugin()
class resnik:
    """
    Constructor:
        resnik(ic, hierarchy=None, use_disjoints=False)
    where
        `ic` is the information content value to use
        `hierarchy` is the hierarchy where the common superclasses are found; if
            `None` is given, then the regular class-subclass hierarchy is used.
        `use_disjoints` is a boolean to indicate whether to take into account
            disjointness information to compute similarity. See Ferreira JD,
            Hastings J, Couto FM (2013). Exploiting disjointness axioms to
            improve semantic similarity measures. Bioinformatics, 29(21),
            2781-2787 for more information.
    
    If `hierarchy` is not None, `use_disjoints` must be False.
    
    Usage:
        .compare(one, two)
    where
        `one` and `two` are concepts
    
    Resnik is a classic semantic similarity method. See Resnik P. (1995). Using
    information content to evaluate semantic similarity in a taxonomy. arXiv
    preprint cmp-lg/9511007.
    """
    
    def __init__(self, ic, hierarchy=None, use_disjoints=False):
        self.shared_ic_calculator = SharedICCalculator(
            ic, hierarchy, use_disjoints)
    
    
    def compare(self, one, two):
        one = utils.get_id(one)
        two = utils.get_id(two)
        
        return self.shared_ic_calculator.get(one, two)


@plugin()
class lin:
    """
    Constructor:
        lin(ic, hierarchy=None, use_disjoints=False)
    where
        `ic` is the information content value to use
        `hierarchy` is the hierarchy where the common superclasses are found; if
            `None` is given, then the regular class-subclass hierarchy is used.
        `use_disjoints` is a boolean to indicate whether to take into account
            disjointness information to compute similarity. See Ferreira JD,
            Hastings J, Couto FM (2013). Exploiting disjointness axioms to
            improve semantic similarity measures. Bioinformatics, 29(21),
            2781-2787 for more information.
    
    If `hierarchy` is not None, `use_disjoints` must be False.
    
    Usage:
        .compare(one, two)
    where
        `one` and `two` are concepts
    
    Lin is a classic semantic similarity method. See Lin D. (1998). An
    information-theoretic definition of similarity. In ICML (Vol. 98, pp.
    296-304).
    """
    
    def __init__(self, ic, hierarchy=None, use_disjoints=False):
        self.ic_calculator = ICCalculator(ic)
        self.shared_ic_calculator = SharedICCalculator(
            ic, hierarchy, use_disjoints)
    
    
    def compare(self, one, two):
        if one == two:
            return 1
        
        one = utils.get_id(one)
        two = utils.get_id(two)
        
        ic_one = self.ic_calculator.get(one)
        ic_two = self.ic_calculator.get(two)
        
        # Special cases
        if ic_one == -1 or ic_two == -1:
            # One of them does not have an IC, so similarity is 0
            return 0
        elif ic_one + ic_two == 0:
            # If both have IC = 0, then IC(MICA) = 0
            # We say, in this case, that similarity is 0
            return 0
        
        num = 2 * self.shared_ic_calculator.get(one, two)
        den = ic_one + ic_two
        return num / den


@plugin()
class jiang:
    """
    Constructor:
        lin(ic, hierarchy=None, use_disjoints=False)
    where
        `ic` is the information content value to use
        `hierarchy` is the hierarchy where the common superclasses are found; if
            `None` is given, then the regular class-subclass hierarchy is used.
        `use_disjoints` is a boolean to indicate whether to take into account
            disjointness information to compute similarity. See Ferreira JD,
            Hastings J, Couto FM (2013). Exploiting disjointness axioms to
            improve semantic similarity measures. Bioinformatics, 29(21),
            2781-2787 for more information.
    
    If `hierarchy` is not None, `use_disjoints` must be False.
    
    Usage:
        .compare(one, two)
    where
        `one` and `two` are concepts
    
    Jiang & Conrath is a classic semantic distance method. It computes a
    distance rather than a similarity measure. See Jiang JJ, Conrath DW (1997).
    Semantic similarity based on corpus statistics and lexical taxonomy. arXiv
    preprint cmp-lg/9709008.
    """
    
    def __init__(self, ic, hierarchy=None, use_disjoints=False):
        self.ic_calculator = ICCalculator(ic)
        self.shared_ic_calculator = SharedICCalculator(
            ic, hierarchy, use_disjoints)
    
    
    def compare(self, one, two):
        if one == two:
            return 0
        
        one = utils.get_id(one)
        two = utils.get_id(two)
        
        ic_one = self.ic_calculator.get(one)
        ic_two = self.ic_calculator.get(two)
        
        # Special cases
        if ic_one == -1 or ic_two == -1:
            # One of them does not have an IC, so similarity is 0
            return 1
        elif ic_one + ic_two == 0:
            # If both have IC = 0, then IC(MICA) = 0
            # We say, in this case, that distance is 1
            return 1
        
        shared_ic = self.shared_ic_calculator.get(one, two)
        return (ic_one + ic_two - 2 * shared_ic) / 2
