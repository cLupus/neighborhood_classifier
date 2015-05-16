# -*- coding: utf-8 -*-
"""
False collection of helper functions for the connector.
"""
__author__ = 'Sindre Nistad'


def select_sql_point(select_criteria=1):
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
    :type select_criteria:  int
    :return:                A SQL clause of SELECT ... FROM ... [WHERE ...]. [] indicates that it might not be there:
                            This is the case for criteria 1, 2, 4, 5
    :rtype:                 str
    """
    if not 1 <= select_criteria <= 6:
        select_criteria = 1
    if select_criteria == 1:
        return "SELECT id, long_lat FROM point "
    elif select_criteria == 2:
        return "SELECT id, long_lat, region FROM point "
    elif select_criteria == 3:
        return "SELECT point.id, point.long_lat, point.region, dataset.id FROM point, region, dataset " \
               "WHERE point.region = region.id AND region.dataset = dataset.id "
    elif select_criteria == 4:
        return "SELECT id, local_location, relative_location, long_lat FROM point "
    elif select_criteria == 5:
        return "SELECT id, local_location, relative_location, long_lat, region FROM point "
    elif select_criteria == 6:
        return "SELECT point.id, point.local_location, point.relative_location, point.long_lat, point.region, " \
               "dataset.id " \
               "FROM point, region, dataset " \
               "WHERE point.region = region.id AND region.dataset = dataset.id "
    else:
        raise Exception("Something very wrong happened...")
