# -*- coding: utf-8 -*-
"""
False collection of helper functions for the connector.
"""
__author__ = 'Sindre Nistad'


def select_sql_point(select_criteria=1, extended_point=False):
    """
        Helper method for getting an appropriate SELECT .. FROM .. [WHERE .. ] query.
    :param select_criteria: Toggles how much information is to be selected for the point:
                                1 -> Selects (id, long_lat) from point
                                2 -> Selects (id, long_lat, region) from point
                                3 -> Selects (id, long_lat, region, dataset.id) from point, and the dataset
                                       (combined with region)
                                4 -> Selects (id, local_location, relative_location, long_lat) from point
                                5 -> Selects (id, local_location, relative_location, long_lat, region) from point
                                6 -> Selects (id, local_location, relative_location, long_lat, region, dataset.id)
                                        from point and the dataset (combined with region)
                                If the mode is different from these, a warning will be issued, and
                                mode 1 will be selected.
    :param extended_point:  Toggles whether or not we are to select from the extended_point table, with is joint with
                            point, region, and dataset.
    :type select_criteria:  int
    :type extended_point:   bool
    :return:                A SQL clause of SELECT ... FROM ... [WHERE ...]. [] indicates that it might not be there:
                            This is the case for criteria 1, 2, 4, 5
    :rtype:                 str
    """
    where_sql = ""
    if not 1 <= select_criteria <= 6:
        select_criteria = 1
    if select_criteria == 1:
        select_sql = "SELECT id, long_lat FROM point "
    elif select_criteria == 2:
        select_sql = "SELECT id, long_lat, region FROM point "
    elif select_criteria == 3:
        if extended_point:
            select_sql = "SELECT id, long_lat, region, dataset FROM extended_point"
        else:
            select_sql = "SELECT point.id, point.long_lat, point.region, dataset.id FROM point, region, dataset "
            where_sql = " WHERE point.region = region.id AND region.dataset = dataset.id "
    elif select_criteria == 4:
        select_sql = "SELECT id, local_location, relative_location, long_lat FROM point "
    elif select_criteria == 5:
        select_sql = "SELECT id, local_location, relative_location, long_lat, region FROM point "
    elif select_criteria == 6:
        if extended_point:
            select_sql = "SELECT id, local_location, relative_location, long_lat, region, dataset " \
                         "FROM extended_point"
        else:
            select_sql = "SELECT point.id, point.local_location, point.relative_location, point.long_lat, " \
                         "point.region, dataset.id " \
                         "FROM point, region, dataset "
            where_sql = " WHERE point.region = region.id AND region.dataset = dataset.id "
    else:
        raise Exception("Something very wrong happened...")

    return select_sql + where_sql


def nearest_neighbor_sql(longitude, latitude, k, extended_point_table=False):
    """
    Gives an ORDER BY clause that gets the k nearest points to the given longitude, and latitude.
    :param longitude:               The longitude of the point we want to find the nearest neighbors.
    :param latitude:                The latitude of the point we want to find the nearest neighbors.
    :param k:                       The number of neighbors we want ot find.
    :param extended_point_table:    Have the extended_point table been created?
    :type longitude:                float
    :type latitude:                 float
    :type k:                        int
    :type extended_point_table:     bool
    :return:                        An ORDER BY SQL clause.
    :rtype:                         str
    """
    if extended_point_table:
        order_by_sql = " ORDER BY long_lat <-> '("
    else:
        order_by_sql = " ORDER BY point.long_lat <-> '("

    # Adding the actual point
    order_by_sql += str(longitude) + ", " + str(latitude) + ")'::point LIMIT " + str(k)
    return order_by_sql
