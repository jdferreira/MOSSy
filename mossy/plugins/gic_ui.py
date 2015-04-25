import sql
import sys
import utils

from parse_config import register


@register()
class sim_ui:
    
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
    

@register()
class sim_gic:
    
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
        with sql.lock:
            sql.cursor.execute(query)
            return sql.cursor.fetchone()[0] or 0
    
    
    def run_union(self, one, two):
        all_ids = ','.join(set(one).union(two))
        
        query = self.union_query.format(all_ids)
        with sql.lock:
            sql.cursor.execute(query)
            return sql.cursor.fetchone()[0] or 0
    
