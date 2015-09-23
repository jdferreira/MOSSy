import logging
import sys

from mossy import sql, utils
from mossy.parse_config import plugin


@plugin()
class sim_ui:
    """
    Constructor:
        sim_ui(hierarchy=None, relevance=None, threshold=None)
    where
        `hierarchy` is the hierarchy where the common superclasses are found; if
            `None` is given, then the regular class-subclass hierarchy is used.
        `relevance` is the name of the measure of relevance to specify which
            concepts are used to compute similarity.
        `threshold` is a numberic value that is associated with `relevance` and
            specifically chooses the concepts that are relevant
    
    Usage:
        .compare(one, two)
    where
        `one` and `two` are concepts or lists of concepts (mixed input is
            allowed)
    
    SIM_UI is a measure defined in Gentleman R (2005). Visualizing and distances
    using GO. The result is the ratio between the number of common superclasses
    and all superclasses of the concepts in `one` and the concepts in `two`
    """
    
    def __init__(self, hierarchy=None, relevance=None, threshold=None):
        
        if relevance is not None:
            sql.assert_identifier(relevance)
        
        if hierarchy is None:
            # This query will select the classes that are part of both sets of
            # superclasses
            self.inter_query = (
                "SELECT COUNT(DISTINCT superclass) "
                "FROM hierarchy ")
            if relevance is not None:
                self.inter_query += (
                    "JOIN relevance ON relevance.id = superclass ")
            self.inter_query += (
                "WHERE subclass IN ({}) AND "
                "      superclass IN ("
                "          SELECT superclass "
                "          FROM hierarchy "
                "          WHERE subclass IN ({})"
                "      ) "
                "")
            if relevance is not None:
                self.inter_query += (
                    "AND relevance.{} >= {}"
                    .format(relevance, sql.conn.escape(threshold)))
            
            # We need to do the same thing for the union of the superclass sets
            self.union_query = (
                "SELECT COUNT(DISTINCT superclass) "
                "FROM hierarchy ")
            if relevance is not None:
                self.union_query += (
                    "JOIN relevance ON relevance.id = superclass ")
            self.union_query += "WHERE subclass IN ({}) "
            if relevance is not None:
                self.union_query += (
                    " AND relevance.{} >= {}"
                    .format(relevance, sql.conn.escape(threshold)))
        
        else:
            self.inter_query = (
                "SELECT COUNT(DISTINCT superclass) "
                "FROM (SELECT superclass "
                "      FROM hierarchy "
                "      WHERE subclass IN ({{0}}) AND "
                "            superclass IN ("
                "                SELECT superclass "
                "                FROM hierarchy "
                "                WHERE subclass IN ({{1}})) "
                "      UNION "
                "      SELECT superclass "
                "      FROM extended_hierarchy "
                "      WHERE extension = {hierarchy} AND "
                "            subclass IN ({{0}}) AND "
                "            superclass IN (SELECT superclass "
                "                           FROM extended_hierarchy "
                "                           WHERE subclass IN ({{1}}) AND "
                "                                 extension = {hierarchy}) "
                .format(hierarchy=sql.conn.escape(hierarchy)))
            if relevance is not None:
                self.inter_query = (
                    "JOIN relevance ON relevance.id = s.superclass "
                    "WHERE relevance.{} >= {}"
                    .format(relevance, sql.conn.escape(threshold)))
            
            self.union_query = (
                "SELECT COUNT(DISTINCT superclass) "
                "FROM (SELECT superclass"
                "      FROM hierarchy "
                "      WHERE subclass IN ({{0}}) "
                "      UNION "
                "      SELECT superclass "
                "      FROM extended_hierarchy "
                "      WHERE extension = {} AND "
                "            subclass IN ({{0}}) "
                "     ) AS s"
                .format(sql.conn.escape(hierarchy)))
            if relevance is not None:
                self.union_query = (
                    "JOIN relevance ON relevance.id = s.superclass "
                    "WHERE relevance.{} >= {}"
                    .format(relevance, sql.conn.escape(threshold)))
    
    def compare(self, one, two):
        # If only one concept is given as either argument, encapsulate it into
        # a list
        one = utils.to_seq(one)
        two = utils.to_seq(two)
        
        # We need to convert to strings since we will build a query string from
        # these ids
        one = [str(i) for i in utils.seq_to_ids(one)]
        two = [str(i) for i in utils.seq_to_ids(two)]
        
        inter = self.run_inter(one, two)
        union = self.run_union(one, two)
        
        return inter / union
    
    
    def run_inter(self, one, two):
        one = ','.join(one)
        two = ','.join(two)
        
        query = self.inter_query.format(one, two)
        with sql.lock:
            sql.cursor.execute(query)
            return sql.cursor.fetchone()[0]
    
    
    def run_union(self, one, two):
        all_ids = ','.join(set(one).union(two))
        
        query = self.union_query.format(all_ids)
        with sql.lock:
            sql.cursor.execute(query)
            return sql.cursor.fetchone()[0]
    

@plugin()
class sim_gic:
    """
    Constructor:
        sim_gic(ic, hierarchy=None, relevance=None, threshold=None)
    where
        `ic` is the information content value to use
        `hierarchy` is the hierarchy where the common superclasses are found; if
            `None` is given, then the regular class-subclass hierarchy is used.
        `relevance` is the name of the measure of relevance to specify which
            concepts are used to compute similarity.
        `threshold` is a numberic value that is associated with `relevance` and
            specifically chooses the concepts that are relevant
    
    Usage:
        .compare(one, two)
    where
        `one` and `two` are concepts or lists of concepts (mixed input is
            allowed)
    
    SIM_GIC is a measure defined in Pesquita C, Faria D, Bastos H, Falcão A,
    Couto F (2007). Evaluating GO-based semantic similarity measures. In Proc.
    10th Annual Bio-Ontologies Meeting (Vol. 37, No. 40, p. 38). The result is
    the ratio between the number of common superclasses and all superclasses
    of the concepts in `one` and the concepts in `two`, where each concept is
    weighted according to its information content.
    """
    
    def __init__(self, ic, hierarchy=None, relevance=None, threshold=None):
        sql.assert_identifier(ic)
        if relevance is not None:
            sql.assert_identifier(relevance)
        
        if ic != "extrinsic":
            table = "intrinsic_ic"
            column = ic
        else:
            table = "extrinsic_ic"
            column = "ic"
        
        if hierarchy is None:
            # This partial query will select the classes that are part of both
            # sets of superclasses
            inner = "SELECT DISTINCT superclass FROM hierarchy "
            if relevance is not None:
                inner += "JOIN relevance ON relevance.id = superclass "
            inner += (
                "WHERE subclass IN ({0}) AND "
                "      superclass IN ("
                "          SELECT superclass "
                "          FROM hierarchy "
                "          WHERE subclass IN ({1})"
                "      ) ")
            if relevance is not None:
                inner += ("AND relevance.{} >= {}"
                          .format(relevance, sql.conn.escape(threshold)))
            
            # This selects the sum of their IC values
            self.inter_query = (
                "SELECT SUM(t.{column}) "
                "FROM {table} AS t "
                "JOIN ({inner}) AS supers ON supers.superclass = t.id"
                .format(table=table, column=column, inner=inner))
            
            # We need to do the same thing for the union of the superclass sets
            inner = "SELECT DISTINCT superclass FROM hierarchy "
            if relevance is not None:
                inner += "JOIN relevance ON relevance.id = superclass "
            inner += "WHERE subclass IN ({}) "
            if relevance is not None:
                inner += ("AND relevance.{} >= {}"
                          .format(relevance, sql.conn.escape(threshold)))
            
            self.union_query = (
                "SELECT SUM(t.{column}) "
                "FROM {table} AS t "
                "JOIN ({inner}) AS supers ON supers.superclass = t.id"
                .format(table=table, column=column, inner=inner))
        
        else:
            
            self.inter_query = (
                "SELECT SUM(t.{column}) "
                "FROM {table} AS t "
                "JOIN (SELECT DISTINCT superclass "
                "      FROM (SELECT superclass "
                "            FROM hierarchy "
                "            WHERE subclass IN ({{0}}) AND "
                "                  superclass IN ("
                "                      SELECT superclass "
                "                      FROM hierarchy "
                "                      WHERE subclass IN ({{1}})) "
                "            UNION "
                "            SELECT superclass "
                "            FROM extended_hierarchy "
                "            WHERE extension = {hierarchy} AND "
                "                  subclass IN ({{0}}) AND "
                "                  superclass IN ("
                "                      SELECT superclass "
                "                      FROM extended_hierarchy "
                "                      WHERE subclass IN ({{1}}) AND "
                "                            extension = {hierarchy}) "
                "           ) AS s "
                "     ) AS supers ON supers.superclass = t.id"
                .format(table=table, column=column,
                        hierarchy=sql.conn.escape(hierarchy)))
            if relevance is not None:
                self.inter_query = (
                    "JOIN relevance ON relevance.id = supers.superclass "
                    "WHERE relevance.{} >= {}"
                    .format(relevance, sql.conn.escape(threshold)))
            
            self.union_query = (
                "SELECT SUM(t.{column}) "
                "FROM {table} AS t "
                "JOIN (SELECT DISTINCT superclass "
                "      FROM (SELECT superclass"
                "            FROM hierarchy "
                "            WHERE subclass IN ({{0}}) "
                "            UNION "
                "            SELECT superclass "
                "            FROM extended_hierarchy "
                "            WHERE extension = {hierarchy} AND "
                "                  subclass IN ({{0}}) "
                "           ) AS s "
                "     ) AS supers ON supers.superclass = t.id"
                .format(table=table, column=column,
                        hierarchy=sql.conn.escape(hierarchy)))
            if relevance is not None:
                self.union_query = (
                    "JOIN relevance ON relevance.id = supers.superclass "
                    "WHERE relevance.{} >= {}"
                    .format(relevance, sql.conn.escape(threshold)))
    
    
    def compare(self, one, two):
        if not one or not two:
            return 0
        
        # If only one concept is given as either argument, encapsulate it into
        # a list
        one = utils.to_seq(one)
        two = utils.to_seq(two)
        
        # We need to convert to strings since we will build a query string from
        # these ids
        one = [str(i) for i in utils.seq_to_ids(one)]
        two = [str(i) for i in utils.seq_to_ids(two)]
        
        inter = self.run_inter(one, two);
        if inter == 0:
            # This happens when there are no common superclasses with IC
            # information. It can happen too that there are no superclasses at
            # all that have IC information, and that would result in the union
            # query returning 0. To avoid dealing with division by 0, we
            # return early. Notice that union >= inter, which means that if
            # inter != 0, then also union != 0
            return 0
        
        union = self.run_union(one, two);
        return inter / union;
    
    
    def run_inter(self, one, two):
        one = ','.join(one)
        two = ','.join(two)
        
        query = self.inter_query.format(one, two)
        logging.debug("INTER query = %s", query)
        with sql.lock:
            sql.cursor.execute(query)
            return sql.cursor.fetchone()[0] or 0
    
    
    def run_union(self, one, two):
        all_ids = ','.join(set(one).union(two))
        
        query = self.union_query.format(all_ids)
        logging.debug("UNION query = %s", query)
        with sql.lock:
            sql.cursor.execute(query)
            return sql.cursor.fetchone()[0] or 0
    
