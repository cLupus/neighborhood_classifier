# -*- coding: utf-8 -*-
"""
False collection of helper functions for the connector.
"""
from warnings import warn

__author__ = 'Sindre Nistad'
from Common.parameters import WAVELENGTHS
from Common.settings import get_extended_point, get_norm_points


def select_sql_point(select_criteria=1):
    """
        Helper method for getting an appropriate SELECT .. FROM .. [WHERE .. ] query.
    NOTE:   If the extended_point table has been created, it will be used when convenient.
    :param select_criteria: Toggles how much information is to be selected for the point:
                                1 -> Selects (id, long_lat) from point
                                2 -> Selects (id, long_lat, region) from point
                                3 -> Selects (id, long_lat, region, dataset.id) from point, and the dataset
                                       (combined with region)
                                4 -> Selects (id, local_location, relative_location, long_lat) from point
                                5 -> Selects (id, local_location, relative_location, long_lat, region) from point
                                6 -> Selects (id, local_location, relative_location, long_lat, region, dataset.id)
                                        from point and the dataset (combined with region)
                                7 -> Selects (id, local_location, relative_location, long_lat, name, region, dataset.id)
                                        from point and the dataset (combined with region)
                                8 -> Selects (id, local_location, relative_location, long_lat, name, sub_name, region,
                                                dataset.id)
                                        from point and the dataset (combined with region)
                                If the mode is different from these, a warning will be issued, and
                                mode 1 will be selected.
    :type select_criteria:  int
    :return:                A SQL clause of SELECT ... FROM ... [WHERE ...]. [] indicates that it might not be there:
                            This is the case for criteria 1, 2, 4, 5
    :rtype:                 str
    """
    where_sql = ""
    min_selection_criteria = 1
    max_selection_criteria = 8
    if not min_selection_criteria <= select_criteria <= max_selection_criteria:
        select_criteria = 1
    if select_criteria == 1:
        select_sql = "SELECT point.id, long_lat FROM point "
    elif select_criteria == 2:
        select_sql = "SELECT point.id, long_lat, region FROM point "
    elif select_criteria == 3:
        if get_extended_point():
            select_sql = "SELECT extended_point.id, long_lat, region, dataset FROM extended_point"
        else:
            select_sql = "SELECT point.id, point.long_lat, point.region, dataset.id FROM point, region, dataset "
            where_sql = " WHERE point.region = region.id AND region.dataset = dataset.id "
    elif select_criteria == 4:
        select_sql = "SELECT point.id, local_location, relative_location, long_lat FROM point "
    elif select_criteria == 5:
        select_sql = "SELECT point.id, local_location, relative_location, long_lat, region FROM point "
    elif select_criteria == 6:
        if get_extended_point():
            select_sql = "SELECT extended_point.id, local_location, relative_location, long_lat, region, dataset " \
                         "FROM extended_point"
        else:
            select_sql = "SELECT point.id, point.local_location, point.relative_location, point.long_lat, " \
                         "point.region, dataset.id " \
                         "FROM point, region, dataset "
            where_sql = " WHERE point.region = region.id AND region.dataset = dataset.id "
    elif select_criteria == 7:
        if get_extended_point():
            select_sql = "SELECT extended_point.id, local_location, relative_location, long_lat, name, region, " \
                         "dataset " \
                         "FROM extended_point"
        else:
            select_sql = "SELECT point.id, point.local_location, point.relative_location, point.long_lat, region.name" \
                         "point.region, dataset.id " \
                         "FROM point, region, dataset "
            where_sql = " WHERE point.region = region.id AND region.dataset = dataset.id "
    elif select_criteria == 8:
        if get_extended_point():
            select_sql = "SELECT extended_point.id, local_location, relative_location, long_lat, extended_point.name, " \
                         "" \
                         "extended_point.sub_name, region, dataset " \
                         "FROM extended_point"
        else:
            select_sql = "SELECT point.id, point.local_location, point.relative_location, point.long_lat, " \
                         "region.name, region.sub_name, point.region, dataset.id " \
                         "FROM point, region, dataset "
            where_sql = " WHERE point.region = region.id AND region.dataset = dataset.id "
    else:
        raise Exception("Something very wrong happened...")

    return select_sql + where_sql


def nearest_neighbor_sql(longitude, latitude, k):
    """
    Gives an ORDER BY clause that gets the k nearest points to the given longitude, and latitude.
    NOTE:   The resulting query will have k + 1, as the nearest point is the point itself, and the result would be the
            k - 1 nearest neighbors.
    NOTE:   If the extended_point table is defined, it will be used wen convenient.
    :param longitude:               The longitude of the point we want to find the nearest neighbors.
    :param latitude:                The latitude of the point we want to find the nearest neighbors.
    :param k:                       The number of neighbors we want ot find.
    :type longitude:                float
    :type latitude:                 float
    :type k:                        int
    :return:                        An ORDER BY SQL clause.
    :rtype:                         str
    """
    if get_extended_point():
        order_by_sql = " ORDER BY long_lat <-> '("
    else:
        order_by_sql = " ORDER BY point.long_lat <-> '("

    # Adding the actual point
    order_by_sql += str(longitude) + ", " + str(latitude) + ")'::point LIMIT " + str(k + 1)
    return order_by_sql


def bands_to_string(dataset, delimiter, wavelength=False):
    """
    Converts the band lengths into a header for the different bands. They will be enumerated if wavelengths is set to
    False, otherwise it will say the wavelength (in micrometer)
    :param dataset:
    :param delimiter:
    :param wavelength:
    :return:
    """
    if dataset == "AVIRIS":
        wavelengths = WAVELENGTHS['AVIRIS']['wavelengths']
    elif dataset == "MASTER":
        wavelengths = WAVELENGTHS['MASTER']['wavelengths']
    else:
        warn("The given dataset ," + str(dataset) + ", does not exist")
        return ""
    string = ""
    if wavelength:
        for wvl in wavelengths:
            string += str(wvl) + delimiter
    else:
        for i in range(len(wavelengths)):
            string += "band " + str(i) + delimiter
    string = string[:-len(delimiter)]
    return string


def dataset_to_string(dataset, single=False):
    """
        A method that takes a single dataset, or a list of datasets, and converts it into a SQL clause:
        'AND (dataset[0] OR dataset[1] OR ... OR dataset[n-1])'. The datasets can be the full name of the dataset
        or it can be the type, e.g. MASTER, or AVIRIS, or a mixture of the two.
    NOTE:   If the table 'extended_point' has been defined, it will be used.
    :param dataset: A single dataset, or a list of datasets that we want to include in a query.
    :param single:          Toggles whether or not the sub query is the only part of the WHERE clause, or not.
                            Default is False.
                            In other words, if this flag is set, the AND (...) will be dropped.
    :type dataset:          str | list of [str]
    :type single:           bool
    :return:        A single string of the form AND (dataset.name = dataset[0] OR ... OR dataset.name = dataset[n-1]) if
                    the given string has only dataset-names in it, or it will return a single string of the form
                    AND (dataset.type = dataset[0] OR ... OR dataset.type = dataset[n-1]) if the datasets have the word
                    'MASTER' or 'AVIRIS' in it. If there is a combination of the two, a combination will be returned.
    :rtype:         str
    """
    if dataset == "" or dataset == []:
        warn("You did not give any databases, so you won't receive a SQL clause, "
             "only a empty string. (dataset_to_string)")
        return ""

    if not isinstance(dataset, list):
        dataset = [dataset]
    if not single:
        dataset_sql = " AND ("
    else:
        dataset_sql = ""
    for elm in dataset:
        if get_extended_point():
            table = ""
        else:
            table = " dataset."
        if 'MASTER' in dataset or 'AVIRIS' in elm:
            dataset_sql += table + "type = '"
        else:
            dataset_sql += table + "name = '"
        dataset_sql += elm + "' OR "
    dataset_sql = dataset_sql[:-3]  # Removing the last 'or '
    if not single:
        dataset_sql += ')'
    return dataset_sql


def get_normalizing_sql(params, datasets="", use_stored_values=True):
    """
    Helper method for getting the SQL for the actual normalizing data specified in params.
    NOTE:   The method will use the 'extended_point', and 'norm_points' table(s) is it is defined.
    :param params:              List of normalizing data to be retried. Can be any combination of 'maximum', 'minimum',
                                'mean', 'standard deviation'.
    :param datasets:            The dataset from which we which to get the normalizing data from. Can be the name of the
                                dataset, or the type. If none is specified (""), it will not consider the datasets.
    :param use_stored_values:   Toggles whether or not we are to use the stored values of the normalizing data in the
                                table 'norm'. If not, we will use the normalizing data from the actual wavelength data
                                in the database.
                                Default is True.
    :return:                    A SQL statement that will get the normalizing data in the form 'band_nr', 'dataset',
                                [[minimum], [maximum], [mean], [stddev]]
    """
    if use_stored_values:
        select_sql = "SELECT band_nr, dataset"
        if 'minimum' in params:
            select_sql += ", minimum"
        if 'maximum' in params:
            select_sql += ", maximum"
        if 'mean' in params:
            select_sql += ", mean"
        if 'standard' in params or 'standard deviation' in params:
            select_sql += ", std_dev"
        select_sql += " FROM norm "

        if datasets != "":
            where_sql = "WHERE " + dataset_to_string(datasets)
        else:
            where_sql = ""
        order_sql = " ORDER BY band_nr ASC "
        sql = select_sql + where_sql + order_sql + ";"
    else:
        values = ""
        if 'minimum' in params:
            values += ", min "
        if 'maximum' in params:
            values += ", max "
        if 'mean' in params:
            values += ", avg "
        if 'standard' in params or 'standard deviation' in params:
            values += ", stddev "
        select_sql = "SELECT band_nr, dataset " + values

        if get_norm_points():
            from_sql = " FROM norm_points "
            where_sql = ""
            group_by_sql = ""
        elif get_extended_point():
            from_sql = " FROM spectrum, extended_point "
            where_sql = " WHERE spectrum.point = extended_point.id "
            group_by_sql = " GROUP BY band_nr, dataset "
        else:
            from_sql = " FROM spectrum, point, region, dataset "
            where_sql = " WHERE point.region = region.id AND region.dataset = dataset.id AND spectrum.point = point.id"
            group_by_sql = " GROUP BY band_nr, dataset.id "
        order_by_sql = " ORDER BY band_nr ASC "
        if datasets != "":
            where_sql += dataset_to_string(datasets)

        sql = select_sql + from_sql + where_sql + group_by_sql + order_by_sql + ';'

    return sql
