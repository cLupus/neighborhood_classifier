# -*- coding: utf-8 -*-
"""
In this file, all the communication between the main program, and the database is handled.
"""

from __future__ import division

from warnings import warn

import pony.orm as pny
from pony.orm import db_session

from Database.database_definition import db, Color, Dataset, Norm, Point, Region, Spectrum, Wavelengths, bind
from Common.parameters import WAVELENGTHS
from Common.common import get_one_indexed, is_in_name, string_to_array, is_gaussian, is_min_max
from RegionOfInterest.region import BasePoint
from RegionOfInterest.region import Point as ROIPoint


__author__ = 'Sindre Nistad'


def connect():
    """
        Performs Database connection using Database settings from settings.py.
    :return:    None
    :rtype:     None
    """
    # return create_engine(URL(**settings.DATABASE))
    bind()
    # return db.get_connection()


def create_tables(overwrite=False, debug=False):
    """
        Creates all the tables necessary for the regions of interest to be in the Database. If 'overwrite' is set to
        True, then, if there is any previous databases with the same name as in settings.py, it will be dropped.
    :param overwrite:   Toggles whether or not the database will be overwritten, or not. Default is False.
                        NB! If set to True, the database will be overwritten!
    :param debug:       Toggles whether or not debug info will be displayed in the console. Default is False.
    :type overwrite:    bool
    :type debug:        bool
    :return:            None
    :rtype:             None
    """
    if overwrite:
        choise = input("Are you really sure you want to overwrite the entire database? This cannot be undone. ")
        if choise.lower() == 'yes' or choise.lower() == 'y':
            overwrite = False
            print("The database will NOT be overwritten. Continuing.")
    db.create_database(overwrite=overwrite, debug=debug)


@db_session
def roi_to_database(roi, add_wavelengths=False, debug=False, force_load=False, commit_at_end=True):
    """
        Writes the content of a region of interest to the database
    :param roi:             The region of interest to be written to the database
    :param add_wavelengths: Toggle whether or not information about wavelengths is to be added. Default is False,
                            as it takes quite a while, and is not strictly necessary.
    :param debug:           Toggle whether or not debug information is to be written to the console. Default is False
    :param force_load:      Toggle whether or not the actual data in the regions of interest is to be read. Default is
                            False
    :param commit_at_end:   Toggles whether or not all the changes are to be committed at the end. Default is False.
    :type roi:              RegionOfInterest.regions_of_interest.RegionsOfInterest
    :type add_wavelengths:  bool
    :type debug:            bool
    :type force_load:       bool
    :type commit_at_end:    bool
    :return:                None
    :rtype:                 None
    """
    # Splits the path by '/', and then '.', and then extracts the name
    dataset_name = roi.path.split('/')[-1].split('.')[0]
    # :type : str
    spectral_type = ""
    if add_wavelengths:
        if is_in_name('AVIRIS', roi.path):
            spectral_type = 'AVIRIS'
        elif is_in_name('MASTER', roi.path):
            spectral_type = 'MASTER'
    if dataset_name not in pny.select(d.name for d in Dataset):
        dataset = add_dataset(dataset_name, spectral_type)
        if not roi.is_loaded:
            print("Now loading the dataset located at " + roi.path)
            roi.load_data()
            rois = roi.get_all()
            print("Loading complete. Now exporting to database.")
    else:
        dataset = pny.get(d for d in Dataset if d.name == dataset_name)
        if force_load:
            print("Now loading the dataset located at " + roi.path)
            rois = roi.get_all(force_load=True)
            print("Loading complete. Now exporting to database.")
        else:
            rois = roi.get_all(force_load=False)  # An empty list []
    if debug:
        print("Adding normalizing data.")
    add_normalizing(roi, dataset, debug)
    if debug:
        print("Normalizing data added.")
    if debug:
        i = 0
        n = len(rois)
    for roi in rois:
        if pny.exists(r for r in Region if r.dataset == dataset and r.name == roi.name and r.sub_name == roi.sub_name):
            if debug:
                print("The point " + roi.name + "_" + roi.sub_name + " is already in the database. SKIPPING.")
                i += 1
            continue
        region = add_region(roi, dataset)
        for point in roi.points:
            # :type point: RegionOfInterest.region.Point
            p = add_point(region, point)
            add_spectrum(p, point.bands)
        if debug:
            i += 1
            print(region.name + " " + str(i / n * 100) + "% COMPLETE")
        if not commit_at_end:
            if debug:
                print("Committing point to the database.")
            db.commit()
            if debug:
                print("Commit completed.")
    if not pny.exists(wvl for wvl in Wavelengths if dataset in wvl.datasets):
        # Does the dataset have any wavelengths associated with its spectra?
        if add_wavelengths:
            if debug:
                print("Adding wavelength information to all points of the dataset")
                print("Spectral type is: " + spectral_type)
            # TODO: Check if this part is really necessary...
            add_wavelength_to_points(spectral_type, dataset)
        if debug:
            print("Committing changes to the database.")
    if commit_at_end:
        db.commit()
        if debug:
            print("Commit complete.")
    if debug:
        print("DONE!")


@db_session
def add_region(roi, dataset):
    """
        Adds the given region to the given data set
    :param roi:     The region of interest we would like to add
    :param dataset: The data set (e.g. MASTER r19) we would like to add the region to.
    :type roi:      RegionOfInterest.region.Region
    :type dataset:  Dataset
    :return:        The added/created database Region
    :rtype:         RegionOfInterest.region.Region
    """
    region = Region(dataset=dataset,
                    name=roi.name,
                    sub_name=roi.sub_name,
                    color=Color(red=roi.rgb[0], green=roi.rgb[1], blue=roi.rgb[2]))
    return region


@db_session
def add_point(region, point):
    """
       Adds the specified point to a region (of interest)
    :param region:  The region to which the point is added
    :param point:   The point which will be added
    :type region:   Database.database_definition.Region
    :type point:    RegionOfInterest.region.Point
    :return:        The added/created point for further 'handling'.
    :rtype:         Database.database_definition.Region
    """
    xy_point = point_to_postgres_point(point.X, point.Y)
    relative_point = point_to_postgres_point(point.map_X, point.map_Y)
    lat_long = point_to_postgres_point(point.latitude, point.longitude)
    p = Point(local_location=xy_point, relative_location=relative_point,
              long_lat=lat_long, region=region)
    return p


@db_session
def add_spectrum(point, bands):
    """
        Adds the given spectrum (the list of bands) to the given point
    :param point:           A point in a region, to which we wish to add a spectral bands
    :param bands:           The spectrum, as discrete bands
    :type point:            Point
    :type bands:            list of [float]
    :return:                None
    :rtype:                 None
    """
    wavelengths = pny.select(wvl for wvl in Wavelengths if point.region.dataset.type == wvl.name)[:]
    for i in range(len(bands)):
        band = bands[i]
        Spectrum(value=band,
                 point=point,
                 band_nr=get_one_indexed(i),
                 wavelength=wavelengths[i])


@db_session
def add_wavelength_to_dataset(dataset, spectral_type, debug=False, commit_at_end=False):
    """
        Adds information about the spectral bands for the given dataset
    :param dataset:         The dataset to which the info is to be added.
    :param spectral_type:   What kind of spectra is it? (e.g. MASTER, or AVIRIS)
    :param commit_at_end:   Toggles whether or not all the changes are to be committed at the end. Default is False.
    :param debug:           Toggles debug/verbose printouts
    :type dataset:          Database.database_definition.Dataset
    :type spectral_type:    str
    :type debug:            bool
    :type commit_at_end:    bool
    :return:
    """
    if debug:
        print("Adding wavelengths to dataset " + str(dataset) + ", having spectral type " + spectral_type)
    wavelengths = WAVELENGTHS[spectral_type]['wavelengths']
    unit = WAVELENGTHS[spectral_type]['unit']
    if pny.exists(wvl for wvl in Wavelengths if wvl.name == dataset.type):
        if debug:
            print("The wavelengths are already in the database, linking dataset to wavelengths")
        # Wavelengths already exists, so we want to add the dataset to the wavelengths
        for wavelength in pny.select(wvl for wvl in Wavelengths if wvl.name == dataset.name):
            wavelength.datasets.add(dataset)
            # TODO: Does this work at all?
    else:
        if debug:
            print("This is a new dataset for the database, generating wavelength information")
        for i in range(len(wavelengths)):
            wavelength = wavelengths[i]
            Wavelengths(name=spectral_type,
                        unit=unit,
                        wavelength=wavelength,
                        datasets=dataset,
                        band_nr=get_one_indexed(i))
    if not commit_at_end:
        db.commit()


@db_session
def add_wavelength_to_points(spectral_type, dataset, commit_at_end=False):
    """
        Adds the wavelength
    :param spectral_type:   The type of spectral data (MASTER/AVIRIS)
    :param dataset:         The dataset to which the wavelength information is to be added
    :param commit_at_end:   Toggles whether or not all the changes are to be committed at the end. Default is False.
    :type spectral_type:    str
    :type dataset:          Dataset
    :type commit_at_end:    bool
    :return:
    """
    # wavelengths = pny.select(w for w in Wavelengths if w.name == spectral_type).order_by(Wavelengths.band_nr)
    #wavelengths = wavelengths[:]  # Make it into a list
    spectralType = spectral_type
    datasetID = dataset.id
    stuff = db.execute(
        """
        SELECT spectrum.id, spectrum.band_nr, spectrum.value, spectrum.point
        FROM spectrum, point, region, dataset
        WHERE spectrum.point = point.id AND
        point.region = region.id AND
        region.dataset = """ + str(datasetID) + ";"
    )
    for (spectrumID, bandNR, value, point) in stuff:
        db.execute(
            """
            UPDATE spectrum SET wavelength = """ + str(bandNR) + """
            WHERE id = (SELECT id FROM wavelengths
                        WHERE name = """ + spectralType + " AND band_nr = " + str(bandNR) + ")"
        )
    if not commit_at_end:
        db.commit()


@db_session
def add_normalizing(roi, dataset, debug=False):
    """
        Adds the normalizing data (max, min, mean, std) to the dataset.
    :param roi:     The regions of interest that are contained in the given dataset.
    :param dataset: The dataset to witch we wish to add normalizing data.
    :param debug:   Flag for toggling debug print-outs on or off. Default is False.
    :type roi:      RegionOfInterest.regions_of_interest.RegionsOfInterest
    :type dataset:  Dataset
    :type debug:    bool
    :return:
    """
    if pny.exists(norm for norm in Norm if dataset == norm.dataset):
        if debug:
            print("The normalization information is already added to this dataset. SKIPPING")
        return
    for i in range(roi.num_bands):
        Norm(dataset=dataset,
             band_nr=get_one_indexed(i),
             maximum=roi.maximums[i],
             minimum=roi.minimums[i],
             mean=roi.means[i],
             std_dev=roi.standard_deviations[i])
    db.commit()


@db_session
def add_dataset(name, spectral_type=""):
    """
        Adds the given name to the database of main data sets. If a spectral type is given, e.g. MASTER, or AVIRIS, than
        it also adds the wavelengths of the given ''data type' to the data set.
    :param name:            The (full) name of the dataset that is to be added.
    :param spectral_type:   Specify the type of specter to be used (e.g. MASTER, or AVIRIS)
    :type name:             str
    :type spectral_type:    str
    :return:                The created Dataset object
    :rtype:                 Dataset
    """
    ds = Dataset(name=name, type=spectral_type)
    if spectral_type:
        add_wavelength_to_dataset(ds, spectral_type)
    return ds


"""
Methods for deleting stuff
"""


def remove_region(name, subname=""):
    """
        Removes the given region from the database.
    :param name:    The name of the region that is to be removed.
    :param subname: The sub-name of the region to be removed. If none is given (""), then all regions which bears the
                    given name will be removed.
    :type name:     str
    :type subname:  str
    :return:        None
    :rtype:         None
    """
    pass
    # db.entities.


"""
Methods for getting stuff from the database
"""
# TODO


def get_points_from_region(region, dataset="", normalizing_mode="", k=0):
    """
        Returns all points, and its k nearest neighbors that are in a given region (can be general (only name),
        or specific (includes sub name). If k is not set explicitly, only the points themselves will be returned. k does
        not include the point itself.
        If the normalizing_mode is set to 'min-max', og 'gaussian', the data will be normalized.
        The dataset is a list, (or a single) data sets the points will be drawn from. If blank, or the list ['MASTER',
        'AVIRIS'], it will return every point which has the given region as name. If one of then, then all points in the
        region which are from the given spectrometer. A specific data set can also be specified, e.g. master_r19... in
        which case, only points in the given data set will be returned. Returns a list of lists of points.
    :param region:              The region points are taken from.
    :param dataset:             The dataset(s) the points are part of. Default is to not place any restrictions.
    :param normalizing_mode:    Toggles whether or not the data is to be normalized, and how the data is to be
                                normalized. Can be 'min-max', or 'gaussian'. Default is none ("").
    :param k:                   The number of neighbors that are to be returned with the point. Default is 0;
                                only the point itself.
    :type region:               str
    :type dataset:              list of [str]
    :type normalizing_mode:     str
    :type k:                    int
    :return:                    List of list of points, with their neighbors
    :rtype:                     list of [list of [RegionOfInterest.region.Point]]
    """
    points = get_sample(region, dataset, -1)
    if k > 0:
        neighborhoods = []
        for point in points:
            neighborhoods.append(get_nearest_neighbors_to_point(point, k, dataset))
        if normalizing_mode != "":
            return normalize(neighborhoods, normalizing_mode)
        return neighborhoods
    else:
        if normalizing_mode != "":
            return normalize(points, normalizing_mode)
        return points


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


@db_session
def get_nearest_neighbors_to_point(point, k, dataset, normalize_mode="",
                                   ignore_dataset=False, select_criteria=3):
    """
        Returns the k-nearest neighbors for the given point. (This method will return k + 1 points in a
        list, as the given point will be included, unless include_point is set to False)
        If the ignore_dataset flag is set to True, we will not care about the points belonging to the same dataset.

        NB: When mode (selection_criteria) 3, or 6 are not selected, the set will not be normalized!
    :param point:           The point we are interested in finding nearest neighbors to.
    :param k:               The number of nearest neighbors we want to find.
    :param dataset:         The dataset(s) we want to get the points from. Can be None, as it is not necessary when
                            ignore_dataset is True, but must be specified if ignore_dataset is True.
    :param ignore_dataset:  Toggles whether or not we will consider the dataset a point belongs to, when searching for
                            nearest neighbor, e.g. ignore to which sensor the data came from. Default is False.
    :param normalize_mode:  Selects the mode of normalization; may be 'min-max', 'gaussian', or "". Default is ""
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
                                NB: When mode 3, or 6 are not selected, the set will not be normalized!
    :type point:            RegionOfInterest.region.Point | Point | RegionOfInterest.region.BasePoint
    :type k:                int
    :type dataset:          list of [str] | str
    :type normalize_mode:   str
    :type ignore_dataset:   bool
    :type select_criteria:  int
    :return:                List of points sorted in ascending order by how close they are to the given point.
    :rtype:                 list of [RegionOfInterest.region.BasePoint | Point]
    """
    assert ((is_min_max(normalize_mode) or is_gaussian(normalize_mode))
            and (select_criteria == 3 or select_criteria == 6) or normalize_mode == "")
    if isinstance(point, Point):
        longitude = point.long_lat[0]
        latitude = point.long_lat[1]
    elif isinstance(point, BasePoint):
        longitude = point.longitude
        latitude = point.latitude
    else:
        raise TypeError("The type for point is not supported. The type of point is ", type(point))
    select_from_sql = select_sql_point(select_criteria)
    order_by_sql = "ORDER BY point.long_lat <-> '(" + str(longitude) + ", " + str(latitude) + ")'::point LIMIT " + str(
        k) + ";"
    if ignore_dataset:
        sql = select_from_sql + order_by_sql
    else:
        if 'WHERE' in select_from_sql:
            dataset_sql = dataset_to_string(dataset)
        elif dataset != "":
            dataset_sql = " WHERE " + dataset_to_string(dataset, True)
        else:
            dataset_sql = ""
        sql = select_from_sql + dataset_sql + order_by_sql
    query = db.execute(sql)
    points = query_to_point_list(query, normalize_mode)
    return points


def get_min_max(datasets="", be_assertive=False):
    """
        Gets a dict of list og minimums, and maximums for each datasets. This can be refined to give the minimums, and
        maximums for specified datasets.
    :param datasets:        A single datasets, or a list of datasets.
    :param be_assertive:    Toggles whether or not we want to assert that the bands are in the right order. By default
                            this is False, but should not be necessary.
    :type datasets:         str | list of [str]
    :type be_assertive:     bool
    :return:                A dict of lists with the minimums and maximums for the given datasets; e.i. two lists, one
                            for maximums, and one for minimums. Each of these contain a dictionary that uses the dataset
                            id as a key and a list of band/a spectrum for each entry.
    :rtype:                 list of [dict of [int, list of [float]]]
    """
    return get_normalizing_data(['minimum', 'maximum'], datasets, be_assertive)


def get_mean_std(datasets="", be_assertive=False):
    """
        Gets a dict of list og means, and standard deviations for each datasets. This can be refined to give the
        means, and standard deviations for specified datasets.
    :param datasets:        A single datasets, or a list of datasets.
    :param be_assertive:    Toggles whether or not we want to assert that the bands are in the right order. By default
                            this is False, but should not be necessary.
    :type datasets:         str | list of [str]
    :type be_assertive:     bool
    :return:                A dict of lists with the means, and standard deviations for the given datasets;
                            e.i. two lists, one for standard deviations, and one for means. Each of these contain a
                            dictionary that uses the dataset id as a key and a list of band/a spectrum for each entry.
    :rtype:                 list of [dict of [int, list of [float]]]
    """
    return get_normalizing_data(['mean', 'standard deviation'], datasets, be_assertive)


def _order_results(order, result):
    """
        Orders the result in the given order, and returns a list of the result
    :param order:   The order in which you want the results.
    :param result:  The dictionary of results from get_normalizing_data
    :type order:    list of [str]
    :type result:   dict of [str, list of [float]]
    :return:        An ordered list of parameters.
    :rtype:         list of [list of [float]]
    """
    l = []
    for elm in order:
        l.append(result[elm])
    return l


@db_session
def get_normalizing_data(params, datasets="", be_assertive=False):
    """
        Gets a dict of list of minimums, maximums, means, and standard deviations for each datasets.
        This can be refined to give the minimums, maximums, means, and std's for specified datasets.
    :param params:          A list of strings specifying which parameters we are interested in.
    :param datasets:        A single datasets, or a list of datasets.
    :param be_assertive:    Toggles whether or not we want to assert that the bands are in the right order. By default
                            this is False, but should not be necessary.
    :type params:           list of [str]
    :type datasets:         str | list of [str]
    :type be_assertive:     bool
    :return:                A dict of lists with the minimums, maximums, means, std's for the given datasets;
                            e.i. four lists, one for maximums, one for minimums, and so on. Each of these contain a
                            dictionary that uses the dataset id as a key and a list of band/a spectrum for each entry.
    :rtype:                 list of [dict of [int, list of [float]]]
    """
    # Creates the appropriate SQL for getting the minimums and maximums
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
    query = db.execute(sql)
    minimums, maximums, means, standard_deviations = {}, {}, {}, {}
    for query_tuple in query:
        band_nr = query_tuple[0]
        dataset = query_tuple[1]
        if 'maximum' in params:
            if dataset not in maximums:
                # We have not yet added the bands for this dataset
                maximums[dataset] = []
            maximum = query_tuple[_index_of_param(params, 'maximum')]
            maximums[dataset].append(maximum)  # Is ordered by band_nr
            if be_assertive:
                assert len(maximums[dataset]) == band_nr

        if 'minimum' in params:
            if dataset not in minimums:
                # We have not yet added the bands for this dataset
                minimums[dataset] = []
            minimum = query_tuple[_index_of_param(params, 'minimum')]
            minimums[dataset].append(minimum)  # Is ordered by band_nr
            if be_assertive:
                assert len(minimums[dataset]) == band_nr

        if 'mean' in params:
            if dataset not in means:
                means[dataset] = []
            mean = query_tuple[_index_of_param(params, 'mean')]
            means[dataset].append(mean)  # Is ordered by band_nr
            if be_assertive:
                assert len(means[dataset]) == band_nr

        if 'standard' in params or 'standard deviation' in params:
            if dataset not in standard_deviations:
                standard_deviations[dataset] = []
            std_dev = query_tuple[_index_of_param(params, 'standard deviation')]
            standard_deviations[dataset].append(std_dev)  # Is ordered by band_nr
            if be_assertive:
                assert len(standard_deviations[dataset]) == band_nr
    # Adding the results
    result = {
        'maximum': maximums,
        'minimum': minimums,
        'mean': means,
        'standard deviation': standard_deviations
    }
    return _order_results(params, result)


def _min_max_normalize(point, minimums, maximums):
    """
    Helper method for normalizing the given point in a min-max fashion.
    :param point:       The point we want to normalize in a min/max fashion.
    :param minimums:    The minimums for the datasets, or a list of maximums fore each band, for this specific point.
    :param maximums:    The maximums for the datasets, or a list of maximums fore each band, for this specific point.
    :type point:        BasePoint
    :type minimums:     dict of [int, list of [float]] | list of [float]
    :type maximums:     dict of [int, list of [float]] | list of [float]
    :return:
    """
    if isinstance(maximums, dict):
        maximums = maximums[point.dataset_id]
    if isinstance(minimums, dict):
        minimums = minimums[point.dataset_id]
    for i in range(len(point.bands)):
        band = point.bands[i]
        band = (band - minimums[i]) / (maximums[i] - minimums[i])
        point.bands[i] = band


def _gaussian_normalize(point, means, std_devs):
    """
    Helper method for normalizing the given point in a min-max fashion.
    :param point:       The point we want to normalize in a min/max fashion.
    :param means:       The means for the datasets, or a list of means for each band, for this specific point.
    :param std_devs:    The standard deviations for the datasets, or a list of standard deviations for each band,
                        for this specific point.
    :type point:        BasePoint
    :type means:        dict of [int, list of [float]] | list of [float]
    :type std_devs:     dict of [int, list of [float]] | list of [float]
    :return:
    """
    if isinstance(means, dict):
        means = means[point.dataset_id]
    if isinstance(std_devs, dict):
        std_devs = std_devs[point.dataset_id]
    for i in range(len(point.bands)):
        band = point.bands[i]
        band = (band - means[i]) / std_devs[i]
        point.bands[i] = band


def normalize(points, mode=""):
    """
        Normalizes the given set of points according to the given mode. If the mode is not set, the method will not do
        anything, but return the point-set.
    :param points:  A list of points we want to normalize.
    :param mode:    The mode of normalization.
    :type points:   list of [BasePoint]
    :type mode:     str
    :return:
    """
    if mode == "":
        warn("No normalizing mode was given, so we're just going to return the points as they are")
    elif is_min_max(mode):
        [minimums, maximums] = get_normalizing_data(['minimum', 'maximum'])
        for point in points:
            if isinstance(point, list):
                for p in point:
                    _min_max_normalize(p, minimums, maximums)
            else:
                _min_max_normalize(point, minimums, maximums)
    elif is_gaussian(mode):
        [means, std_dev] = get_mean_std()
        for point in points:
            if isinstance(point, list):
                for p in point:
                    _gaussian_normalize(p, means, std_dev)
            else:
                _gaussian_normalize(point, means, std_dev)
    else:
        warn("The given mode is unknown. Returning the points as they were")
    return points


def query_to_point_list(query, normalize_mode=""):
    """
        Takes a query of points (id, long_lat, region), or everything from point, gets the spectrum for each point,
        and then creates a list of BasePoints, or Points.
        If you want a point, the query has to have the following
        (id, local_location, relative_location, long_lat, region)
    :param query:           The query, which has selected (id, region, long_lat) for the points.
    :param normalize_mode:  Is the data to be normalized? Can be blank "" -> No normalization. 'min-max' -> normalizes
                            the data by minimums, and maximums (rescales). 'gaussian' -> (val - mean) / std.
                            Default is no normalization.
    :type query:            psycopg2.extensions.cursor
    :type normalize_mode:   str
    :return:                List of BasePoints/Points with their spectrum.
    :rtype:                 list of [RegionOfInterest.region.BasePoint | RegionOfInterest.region.Point]
    """
    points = []
    for point_tuple in query:
        points.append(get_point(point_tuple))
    if normalize_mode != "":
        points = normalize(points, normalize_mode)
    return points


@db_session
def get_point(point_tuple):
    """
        Takes a tuple, and makes it into a Point, or BasePoint depending on how long the tuple is. This method will also
        get the spectrum for the given point as well
    :param point_tuple: Tuple of numbers representing a point. May be the following:
                            * (id, long_lat, [region], [dataset]) or
                            * (id, local_location, relative_location, long_lat, [region], [dataset]),
                        where [] is optional, and might be used in the future.
    :type point_tuple:  tuple
    :return:            A single point (Point or BasePoint) that is equivalent to the given tuple.
    :rtype:             BasePoint | RegionsOfInterest.region.Point
    """
    point_id = point_tuple[0]
    sql = "SELECT value FROM spectrum WHERE point = " + str(point_id) + " ORDER BY band_nr;"
    query = db.execute(sql)
    bands = [value[0] for value in query]
    if 2 <= len(point_tuple) <= 4:
        long_lat = string_to_array(point_tuple[1])
        longitude = long_lat[0]
        latitude = long_lat[1]
        # We only have enough info to give a BasePoint
        if len(point_tuple) >= 3:
            region = point_tuple[2]
        else:
            region = -1
        if len(point_tuple) == 4:
            dataset = point_tuple[3]
        else:
            dataset = -1
        return BasePoint(point_id, latitude, longitude, bands, region, dataset)
    elif 4 <= len(point_tuple) <= 6:
        # We have more info, and so we make a 'normal' Point.
        local_location = string_to_array(point_tuple[1])
        relative_location = string_to_array(point_tuple[2])
        long_lat = string_to_array(point_tuple[3])
        x = local_location[0]
        y = local_location[1]
        map_x = relative_location[0]
        map_y = relative_location[1]
        longitude = long_lat[0]
        latitude = long_lat[1]
        if len(point_tuple) >= 5:
            region = point_tuple[4]
        else:
            region = -1
        if len(point_tuple) == 6:
            dataset = point_tuple[5]
        else:
            dataset = -1
        return ROIPoint(point_id, x, y, map_x, map_y, longitude, latitude, region, dataset)


@db_session
def get_sample(area, dataset, number_of_samples, background=False, random_sample=False):
    """
        Returns a random sample of number_of_samples points which lies in the given area (which may be regions, or a
        specific region when given a sub-name; e.g. name_sub-name, or just name for the value of area. If background
        is set to True, the resulting collection will be a random sample of anything but the given area.
    :param area:                Name of the region we want the sample to be from (or not from). If the underscore
                                character is in the name, it will be assumed as a sub-region,
                                e.i. sub_name will be given.
    :param dataset:             The dataset to which the points we want to sample from belong. This can be the empty
                                string, in which case, we cont care about the dataset. It can also be an array of
                                datasets, and which case the points can be from any of them.
    :param number_of_samples:   The number of samples we want. This can be set to -1 (negative) in which case, every
                                point that satisfy the query is selected.
    :param background:          Toggles whether or not the returned set is from the actual region, or from the
                                'background' of that region, e.i. anything but that region.
    :param random_sample:       Toggles whether or not the sample is to be randomized or not. Default is not, as it is
                                expensive (at the moment).
    :type area:                 str
    :type dataset:              str | list of [str]
    :type number_of_samples:    int
    :type background:           bool
    :type random_sample:        bool
    :return:                    A list of points which constitutes a sample from the given region, or a list of points
                                constitutes a sample from the background of that region.
    :rtype:                     list of [RegionOfInterest.region.Point]
    """
    # Splitting the area-name into (general) name, and sub name
    if '_' in area:
        name = area.split('_')[0]
        sub_name = area.split('_')[1]
    else:
        name = area
        sub_name = ""

    # Writing the SQL query
    select_sql = "SELECT point.id, long_lat, point.region FROM point, region "
    if dataset != "":
        select_sql += ", dataset "
        dataset_sql = dataset_to_string(dataset)
    else:
        dataset_sql = ""
    if background:
        # Are we sampling the background or not?
        equal_operator = " != "
    else:
        equal_operator = " = "
    where_sql = " WHERE point.region = region.id AND region.name" + equal_operator + "'" + name + "'"
    if sub_name != "":
        where_sql += " AND region.sub_name" + equal_operator + "'" + sub_name + "'"
    if random_sample:
        order_by_sql = " ORDER BY random() "
        # TODO: Fix the random selection; according to StackOverflow, this is VERY slow (sorts the entire table).
        # There are remedies, but they are difficult to work on when constraining the data.
    else:
        order_by_sql = ""
    if number_of_samples > 0:
        limit_sql = " LIMIT " + str(number_of_samples)
    else:
        limit_sql = ""
    sql = select_sql + where_sql + dataset_sql + order_by_sql + limit_sql + ";"
    query = db.execute(sql)
    return query_to_point_list(query)


def point_to_postgres_point(*args):
    """
        Converts the list of numbers in 'args' to a Postgresql point. This is so that arbitrary
        dimensionality is supported
    :param args:    list of points to be converted
    :type args:     list of [float]
    :return:        A single string representing a point object in Postgres with the given coordinates.
    :rtype:         str
    """
    s = ""
    for elm in args:
        s += str(elm) + ', '
    s = s[:-2]  # Removes the last ", "
    return s


def dataset_to_string(dataset, single=False):
    """
        A method that takes a single dataset, or a list of datasets, and converts it into a SQL clause:
        'AND (dataset[0] OR dataset[1] OR ... OR dataset[n-1])'. The datasets can be the full name of the dataset
        or it can be the type, e.g. MASTER, or AVIRIS, or a mixture of the two.
    :param dataset: A single dataset, or a list of datasets that we want to include in a query.
    :param single:  Toggles whether or not the sub query is the only part of the WHERE clause, or not. Default is False.
                    In other words, if this flag is set, the AND (...) will be dropped.
    :type dataset:  str | list of [str]
    :type single:   bool
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
        if 'MASTER' in dataset or 'AVIRIS' in elm:
            dataset_sql += "dataset.type = '"
        else:
            dataset_sql += " dataset.name = '"
        dataset_sql += elm + "' OR "
    dataset_sql = dataset_sql[:-3]  # Removing the last 'or '
    if not single:
        dataset_sql += ')'
    return dataset_sql


def _index_of_param(param, val):
    """
        Returns the index for the given val e.g. 'ma' for maximum, 'mi', for minimum, etc. for the given param, which
        can be a single string of abbreviations, or a list of string names for the parameters we want, e.g. 'maximum',
        'minimum', 'mean', 'standard deviation'. The index starts at 2, because the first two elements in the tuple, is
        the id, and the band number.
    :param param:   A string, or array of strings which specify what parameters we want to get from the query.
    :param val:     The specific value (e.g. max, min, etc.) we want the index.
    :type param:    list of [str]
    :type val:      str
    :return:        The index of the given value in the param
    :rtype:         int
    """
    index_shift = 2
    relative_index = param.index(val)
    return relative_index + index_shift
