# -*- coding: utf-8 -*-
"""
In this file, all the communication between the main program, and the database is handled.
"""

from __future__ import division

from warnings import warn

import pony.orm as pny
from pony.orm import db_session
import numpy as np

from Database.helpers import select_sql_point, nearest_neighbor_sql
from Database.database_definition import db, Color, Dataset, Norm, Point, Region, Spectrum, Wavelengths, bind
from Common.parameters import WAVELENGTHS, NUMBER_OF_USED_BANDS, USE_NAIVE_SAMPLING, UNIQUE_CLASSES, POINT_FIELDS
from Common.common import get_one_indexed, is_in_name, string_to_array, is_gaussian, is_min_max
from RegionOfInterest.region import BasePoint
from RegionOfInterest.region import Point as ROIPoint

# TODO: Use IOPro if available

__author__ = 'Sindre Nistad'

__extended_point_table = False


@db_session
def connect(combine_point_and_dataset=False):
    """
        Performs Database connection using Database settings from settings.py.
    :param combine_point_and_dataset:   Toggles whether or not a temporary table is to be created that stores the union
                                        of points, regions, and datasets. Default is False.
                                        The purpose of this is to speed up getting stuff from the database.
    :type combine_point_and_dataset:    bool
    :return:    None
    :rtype:     None
    """
    try:
        bind()
    except TypeError:
        warn("The database has already been bound.")
    if combine_point_and_dataset:
        sql = """
        CREATE TEMPORARY TABLE extended_point AS
            SELECT
                point.id,
                local_location,
                relative_location,
                long_lat,
                region,
                dataset,
                region.name,
                region.sub_name,
                color,
                dataset.name AS dataset_name,
                type
            FROM point, region, dataset
            WHERE point.region = region.id AND region.dataset = dataset.id;
        """
        db.execute(sql)
        global __extended_point_table
        __extended_point_table = True


def disconnect(cleanup=True):
    if cleanup:
        _cleanup()
    db.disconnect()


@db_session
def _cleanup():
    global __extended_point_table
    if __extended_point_table:
        sql = "DROP TABLE extended_point;"
        db.execute(sql)
    db.commit()
    __extended_point_table = False


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


def export_to_csv(region="", dataset="", k=0, delimiter=','):
    delimiter += " "
    if region == "":
        # Export all the regions
        points = []
        """ :type list[ROIPoint] """
        file_name = "dataset.csv"
        for sample_region in UNIQUE_CLASSES:
            points.extend(get_sample(sample_region, dataset, -1, k=k, select_criteria=8))
    else:
        points = get_sample(region, dataset, -1, k=k, select_criteria=8)
        file_name = region + ".csv"
    f = open(file_name, 'w')
    for point in points:
        # @type point: ROIPoint
        string = point.name + delimiter + str(point.sub_name) + delimiter + point.get_bands_as_string(delimiter)
        f.write(string + "\n")
    f.close()


def get_dataset_sample(target_area, k=0, normalizing_mode="gaussian", dataset="", number_of_samples=-1,
                       background_target_ratio=1.0, random_sample=False):
    """

    :param target_area:         Name of the region we want the sample to be from (or not from). If the underscore
                                character is in the name, it will be assumed as a sub-region,
                                e.i. sub_name will be given.
    :param dataset:             The dataset to which the points we want to sample from belong. This can be the empty
                                string, in which case, we cont care about the dataset. It can also be an array of
                                datasets, and which case the points can be from any of them.
    :param number_of_samples:   The number of samples we want. This can be set to -1 (negative) in which case, every
                                point that satisfy the query is selected.
    :param k:                   The number of neighbors to each point we want to get.
    :param random_sample:       Toggles whether or not the sample is to be randomized or not. Default is not, as it is
                                expensive (at the moment).
    :type target_area:          str
    :type dataset:              str | list of [str]
    :type number_of_samples:    int
    :type k:                    int
    :type random_sample:        bool
    :return:                    A list of points which constitutes a sample from the given region, or a list of points
                                constitutes a sample from the background of that region.
    :rtype:                     list of [RegionOfInterest.region.Point]
    """
    # Getting the points
    targets = get_sample(target_area, dataset, number_of_samples, k, 3, False, random_sample)
    num_background = int(round(len(targets) * background_target_ratio))
    background = get_sample(target_area, dataset, num_background, k, 3, True, random_sample)

    # Normalizing the points
    targets = normalize(targets, normalizing_mode)
    background = normalize(background, normalizing_mode)

    # Convert to NumPy arrays
    targets = convert_points_to_numpy_array(targets, False)
    background = convert_points_to_numpy_array(background, True)

    return np.vstack([targets, background])


def get_numpy_array_from_region(region, dataset="", normalizing_mode="", k=0):
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
    :return:                    A 2D NumPy array of spectral data, each point corresponding to one column if k = 0;
                                we do not consider the neigborhood. If we do consider the neighborhood, then it returns
                                a 3D NumPy array; each column is a neighborhood, and each column in that matrix is a
                                'point';
    :rtype:
    """
    points = get_points_from_region(region, dataset, normalizing_mode, k)
    return convert_points_to_numpy_array(points)


def convert_points_to_numpy_array(points, background=False):
    """
    Converts a list of points, or neighbors to a numpy array of appropriate size.
    :param points:      A list (of list) of points that will be converted into a numpy array/matrix.
    :param background:  Toggles whether or not these points are to be considered as part of the background or not.
                        Default is False.
    :type points:       list of [BasePoint] | list of [list of [BasePoint]]
    :type background:   bool
    :return:            A 2D NumPy array of spectral data, each point corresponding to one column if k = 0;
                        we do not consider the neigborhood. If we do consider the neighborhood, then it returns
                        a 3D NumPy array; each column is a neighborhood, and each column in that matrix is a 'point';
    """
    if isinstance(points[0], BasePoint):
        num_neighbors = 0
    else:
        num_neighbors = len(points[0])
    # TODO: Make it possible to combine different datasets (MASTER/AVIRIS)
    if num_neighbors == 0:
        band_matrix = np.array([point.get_bands(background) for point in points])
    else:
        # band_matrix = [[p.bands for p in neighbor] for neighbor in points]
        band_matrix = [None] * len(points)
        for i in range(len(points)):
            neighbors = points[i]
            flag = 0 if background else 1
            itm = [flag]
            itm.extend([point.bands for point in neighbors])
            band_matrix[i] = np.array(itm)
            # TODO: Make into a single list.
    return band_matrix


def get_numpy_sample(area, dataset, number_of_samples, k=0, select_criteria=1, background=False, random_sample=False):
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
    :param k:                   The number of neighbors to each point we want to get.
    :param select_criteria:     Toggles how much information is to be selected for the point:
                                    1 -> Selects (id, long_lat) from point
                                    2 -> Selects (id, long_lat, region) from point
                                    3 -> Selects (id, long_lat, region, dataset.id) from point, and the dataset
                                           (combined with region)
                                    4 -> Selects (id, local_location, relative_location, long_lat) from point
                                    5 -> Selects (id, local_location, relative_location, long_lat, region) from point
                                    6 -> Selects (id, local_location, relative_location, long_lat, region, dataset.id)
                                            from point and the dataset (combined with region)
                                    7 -> Selects (id, local_location, relative_location, long_lat, name, region,
                                    dataset.id)
                                        from point and the dataset (combined with region)
                                    8 -> Selects (id, local_location, relative_location, long_lat, name, sub_name,
                                    region,
                                                dataset.id)
                                        from point and the dataset (combined with region)
                                If the mode is different from these, a warning will be issued, and
                                mode 1 will be selected.
                                NB: When mode 3, or 6 is NOT selected, the set will not be normalized!
                                Default is 1.
    :param background:          Toggles whether or not the returned set is from the actual region, or from the
                                'background' of that region, e.i. anything but that region.
    :param random_sample:       Toggles whether or not the sample is to be randomized or not. Default is not, as it is
                                expensive (at the moment).
    :type area:                 str
    :type dataset:              str | list of [str]
    :type number_of_samples:    int
    :type k:                    int
    :type select_criteria:      int
    :type background:           bool
    :type random_sample:        bool
    :return:                    A NumPy array/matrix of samples
    :rtype:                     np.array
    """
    points = get_sample(area, dataset, number_of_samples, k, select_criteria, background, random_sample)
    return convert_points_to_numpy_array(points, background)




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
    if normalizing_mode == "":
        # We are not interested in normalizing the data
        select_criteria = 1
    else:
        select_criteria = 3
    points = get_sample(region, dataset, -1, select_criteria=select_criteria)
    if k > 0:
        neighborhoods = [None] * len(points)
        for i in range(len(points)):
            point = points[i]
            neighborhoods[i] = get_nearest_neighbors_to_point(point, k, dataset)
        if normalizing_mode != "":
            return normalize(neighborhoods, normalizing_mode)
        return neighborhoods
    else:
        if normalizing_mode != "":
            return normalize(points, normalizing_mode)
        return points


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
                                7 -> Selects (id, local_location, relative_location, long_lat, name, region, dataset.id)
                                        from point and the dataset (combined with region)
                                8 -> Selects (id, local_location, relative_location, long_lat, name, sub_name, region,
                                                dataset.id)
                                        from point and the dataset (combined with region)
                                If the mode is different from these, a warning will be issued, and
                                mode 1 will be selected.
                                NB: When mode 3, or 6 is NOT selected, the set will not be normalized!
    :type point:            RegionOfInterest.region.Point | Point | RegionOfInterest.region.BasePoint
    :type k:                int
    :type dataset:          list of [str] | str
    :type normalize_mode:   str
    :type ignore_dataset:   bool
    :type select_criteria:  int
    :return:                List of points sorted in ascending order by how close they are to the given point.
    :rtype:                 list of [RegionOfInterest.region.BasePoint | Point]
    """
    # Is the normalizing mode compatible with the SELECT criteria?
    assert ((is_min_max(normalize_mode) or is_gaussian(normalize_mode))
            and (select_criteria == 3 or 6 <= select_criteria <= 8) or normalize_mode == "")

    # Getting the longitude, and latitude
    if isinstance(point, Point):
        longitude = point.long_lat[0]
        latitude = point.long_lat[1]
    elif isinstance(point, BasePoint):
        longitude = point.longitude
        latitude = point.latitude
    else:
        raise TypeError("The type for point is not supported. The type of point is ", type(point))

    # Selecting the appropriate SELECT clause, followed by a ORDERED BY clause
    select_from_sql = select_sql_point(select_criteria, __extended_point_table)

    # Initial ORDER BY clause (what attribute are we compare against?)
    order_by_sql = nearest_neighbor_sql(longitude, latitude, k, __extended_point_table)

    # Do we consider the dataset the points belong to?
    dataset_sql = ""
    if not ignore_dataset:
        if 'WHERE' in select_from_sql:
            dataset_sql = dataset_to_string(dataset)
        elif dataset != "":
            dataset_sql = " WHERE " + dataset_to_string(dataset, True)

    # There is no need for enforcing the areas to be of the same type, as it might be important that the neighbor
    # is of a different region

    sql = select_from_sql + dataset_sql + order_by_sql + ";"

    # Execute the generated SQL
    query = db.execute(sql)

    # Converting the query result to normal points.
    points = query_to_point_list(query, normalize_mode)
    points.sort()
    return points


def get_nearest_neighbor_to_points(points, k, dataset, normalize_mode="",
                                   ignore_dataset=False, select_criteria=3):
    """
        This method does the same as get_nearest_neighbor_to_point for a list of points.
        Returns the k-nearest neighbors for the given points. (This method will return k + 1 points in a
        list, as the given point will be included, unless include_point is set to False)
        If the ignore_dataset flag is set to True, we will not care about the points belonging to the same dataset.

        NB: When mode (selection_criteria) 3, or 6 are not selected, the set will not be normalized!
    :param points:          The list of points we are interested in finding nearest neighbors to.
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
                                7 -> Selects (id, local_location, relative_location, long_lat, name, region, dataset.id)
                                        from point and the dataset (combined with region)
                                8 -> Selects (id, local_location, relative_location, long_lat, name, sub_name, region,
                                                dataset.id)
                                        from point and the dataset (combined with region)
                                If the mode is different from these, a warning will be issued, and
                                mode 1 will be selected.
                                NB: When mode 3, or 6 is NOT selected, the set will not be normalized!
    :type points:           list of [RegionOfInterest.region.Point | Point | RegionOfInterest.region.BasePoint]
    :type k:                int
    :type dataset:          list of [str] | str
    :type normalize_mode:   str
    :type ignore_dataset:   bool
    :type select_criteria:  int
    :return:                list of List of points sorted in ascending order by how close they are to the given point.
                            One list for each point in the input list.
    :rtype:                 list of [list of [RegionOfInterest.region.BasePoint | Point]]
    """
    neighbors = [None] * len(points)
    for i in range(len(points)):
        point = points[i]
        neighbors[i] = get_nearest_neighbors_to_point(point, k, dataset, normalize_mode, ignore_dataset,
                                                      select_criteria)
    return neighbors


def get_min_max(datasets="", be_assertive=False, take_averages=False):
    """
        Gets a dict of list og minimums, and maximums for each datasets. This can be refined to give the minimums, and
        maximums for specified datasets.
    :param datasets:        A single datasets, or a list of datasets.
    :param be_assertive:    Toggles whether or not we want to assert that the bands are in the right order. By default
                            this is False, but should not be necessary.
    :param take_averages:   Toggles whether or not the average value of the normalizing data (over datasets) is to be
                            used or not. Default is False.
    :type datasets:         str | list of [str]
    :type be_assertive:     bool
    :type take_averages:    bool
    :return:                A dict of lists with the minimums and maximums for the given datasets; e.i. two lists, one
                            for maximums, and one for minimums. Each of these contain a dictionary that uses the dataset
                            id as a key and a list of band/a spectrum for each entry.
    :rtype:                 list of [dict of [int, list of [float]]]
    """
    return get_normalizing_data(['minimum', 'maximum'], datasets, be_assertive, take_averages)


def get_mean_std(datasets="", be_assertive=False, take_averages=False):
    """
        Gets a dict of list og means, and standard deviations for each datasets. This can be refined to give the
        means, and standard deviations for specified datasets.
    :param datasets:        A single datasets, or a list of datasets.
    :param be_assertive:    Toggles whether or not we want to assert that the bands are in the right order. By default
                            this is False, but should not be necessary.
    :param take_averages:   Toggles whether or not the average value of the normalizing data (over datasets) is to be
                            used or not. Default is False.
    :type datasets:         str | list of [str]
    :type be_assertive:     bool
    :type take_averages:    bool
    :return:                A dict of lists with the means, and standard deviations for the given datasets;
                            e.i. two lists, one for standard deviations, and one for means. Each of these contain a
                            dictionary that uses the dataset id as a key and a list of band/a spectrum for each entry.
    :rtype:                 list of [dict of [int, list of [float]]]
    """
    return get_normalizing_data(['mean', 'standard deviation'], datasets, be_assertive, take_averages)


def _average_over_datasets(data):
    """
    Takes the averages over the datasets in data for each attribute, minimum, maximum, mean, and standard deviation.
    :param data:    The data to be averaged.
    :type data:     dict of [str, dict of [int, list of [float]]]
    :return:        A dict with the same keys, minimum, maximum, mean, and standard deviation.
    :rtype:         dict of [str, list of [float]]
    """
    result = {}
    for key in data.keys():
        normalizing_attribute = data[key]  # e.i. Max, min, etc.
        result[key] = {
            'MASTER': [0] * NUMBER_OF_USED_BANDS['MASTER'],
            'AVIRIS': [0] * NUMBER_OF_USED_BANDS['AVIRIS'],
            'num_MASTER': 0,
            'num_AVIRIS': 0
        }
        for dataset in normalizing_attribute.keys():
            if len(dataset) == NUMBER_OF_USED_BANDS['MASTER']:
                result['MASTER'] = [dataset[i] + result['MASTER'] for i in range(len(dataset))]
                result['num_MASTER'] += 1
            elif len(dataset) == NUMBER_OF_USED_BANDS['AVIRIS']:
                result['AVIRIS'] = [dataset[i] + result['AVIRIS'] for i in range(len(dataset))]
                result['num_AVIRIS'] += 1
    result['MASTER'] = [band / result['num_MASTER'] for band in result['MASTER']]
    result['AVIRIS'] = [band / result['num_AVIRIS'] for band in result['AVIRIS']]
    return {'MASTER': result['MASTER'], 'AVIRIS': result['AVIRIS']}


@db_session
def get_normalizing_data(params, datasets="", be_assertive=False, take_averages=False):
    """
        Gets a dict of list of minimums, maximums, means, and standard deviations for each datasets.
        This can be refined to give the minimums, maximums, means, and std's for specified datasets.
    :param params:          A list of strings specifying which parameters we are interested in.
    :param datasets:        A single datasets, or a list of datasets.
    :param be_assertive:    Toggles whether or not we want to assert that the bands are in the right order. By default
                            this is False, but should not be necessary.
    :param take_averages:   Toggles whether or not the average value of the normalizing data (over datasets) is to be
                            used or not. Default is False.
    :type params:           list of [str]
    :type datasets:         str | list of [str]
    :type be_assertive:     bool
    :type take_averages:    bool
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
                # TODO: Set initial size, to speed thing up
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
    if take_averages:
        result = _average_over_datasets(result)
    return _order_results(params, result)


def normalize(points, mode=""):
    """
        Normalizes the given set of points according to the given mode. If the mode is not set, the method will not do
        anything, but return the point-set.
    :param points:  A list of points we want to normalize.
    :param mode:    The mode of normalization.
    :type points:   list of [BasePoint] | list of [list of [BasePoint]]
    :type mode:     str
    :return:        List of normalized points
    :rtype:         list of [BasePoint]
    """
    if (isinstance(points[0], BasePoint) and points[0].dataset_id < 0) or (
                isinstance(points[0], list) and points[0][0].dataset_id < 0):
        take_averages = True
    else:
        take_averages = False
    if mode == "":
        warn("No normalizing mode was given, so we're just going to return the points as they are")
    elif is_min_max(mode):
        [minimums, maximums] = get_normalizing_data(['minimum', 'maximum'], take_averages=take_averages)
        for point in points:
            if isinstance(point, list):
                for p in point:
                    _min_max_normalize(p, minimums, maximums)
            else:
                _min_max_normalize(point, minimums, maximums)
    elif is_gaussian(mode):
        [means, std_dev] = get_mean_std(take_averages=take_averages)
        for point in points:
            if isinstance(point, list):
                for p in point:
                    _gaussian_normalize(p, means, std_dev)
            else:
                _gaussian_normalize(point, means, std_dev)
    else:
        warn("The given mode is unknown. Returning the points as they were")
    return points


def _get_description(description):
    res = {}
    for i in range(len(description)):
        res[description[i][0]] = i
    return res

def query_to_point_list(query, normalize_mode="", number_of_elements=-1, user_row_count=False, background=False):
    """
        Takes a query of points (id, long_lat, region), or everything from point, gets the spectrum for each point,
        and then creates a list of BasePoints, or Points.
        If you want a point, the query has to have the following
        (id, local_location, relative_location, long_lat, region)
    :param query:               The query, which has selected (id, region, long_lat) for the points.
    :param normalize_mode:      Is  the data to be normalized? Can be blank "" -> No normalization.
                                'min-max' -> normalizes the data by minimums, and maximums (rescales).
                                'gaussian' -> (val - mean) / std. Default is no normalization.
    :param number_of_elements:  To speed things up, you can specify the number number of elements that will be in the
                                query.
    :param user_row_count:      Toggles whether or not to use the rowcount filed in the query as a parameter of length.
                                Default is False.
                                NOTE: This will overwrite whatever value of number_of_elements was passed.
    :param background:          Is this considered background, or target? Default is False.
                                Sets the first element to 0 if True, or 1 if False, i.e. 1 if the pointlist is the
                                target, and 0 if it is background.
    :type query:                psycopg2.extensions.cursor
    :type normalize_mode:       str
    :type number_of_elements:   int
    :type user_row_count:       bool
    :type background:           bool
    :return:                    List of BasePoints/Points with their spectrum.
    :rtype:                     list of [RegionOfInterest.region.BasePoint | RegionOfInterest.region.Point]
    """
    description = _get_description(query.description)
    if user_row_count:
        number_of_elements = query.rowcount
    if number_of_elements > 0:
        points = [None] * number_of_elements
        i = 0
        for point_tuple in query:
            points[i] = get_point(point_tuple, description)
            i += 1
    else:
        points = []
        for point_tuple in query:
            points.append(get_point(point_tuple, description))
    if normalize_mode != "":
        points = normalize(points, normalize_mode)
    return points


@db_session
def get_point(point_tuple, description):
    """
        Takes a tuple, and makes it into a Point, or BasePoint depending on how long the tuple is. This method will also
        get the spectrum for the given point as well
    :param point_tuple: Tuple of numbers representing a point. May be the following:
                            * (id, long_lat, [region], [dataset]) or
                            * (id, local_location, relative_location, long_lat, [name], [sub_name], [region], [dataset]),
                        where [] is optional, and might be used in the future.
    :param description: A dictionary of columns names with their associated index in the tuple.
    :type point_tuple:  tuple
    :type description:  dict of [str, int]
    :return:            A single point (Point or BasePoint) that is equivalent to the given tuple.
    :rtype:             BasePoint | RegionsOfInterest.region.Point
    """
    point_id = point_tuple[0]
    sql = "SELECT value FROM spectrum WHERE point = " + str(point_id) + " ORDER BY band_nr;"
    query = db.execute(sql)
    bands = [value[0] for value in query]
    values = {}
    for key in POINT_FIELDS:
        if key in description:
            values[key] = point_tuple[description[key]]
        else:
            values[key] = ""
    point_id = values['id']
    long_lat = string_to_array(values['long_lat'])
    longitude = long_lat[0]
    latitude = long_lat[1]
    region = values['region']
    dataset = values['dataset']
    if 'local_location' not in description:
        return BasePoint(point_id, latitude, longitude, bands, region, dataset)
    else:
        local_location = string_to_array(values['local_location'])
        relative_location = string_to_array(values['relative_location'])
        x = local_location[0]
        y = local_location[1]
        map_x = relative_location[0]
        map_y = relative_location[1]
        name = values['name']
        sub_name = values['sub_name']
        return ROIPoint(point_id, x, y, map_x, map_y, latitude, longitude, bands, name, sub_name, region, dataset)


@db_session
def get_total_number_of_samples():
    """
    Returns the total number of points in the database
    :return:
    :rtype:     int
    """
    sql = "SELECT count(*) FROM point;"
    query = db.execute(sql)
    for itm in query:
        return itm[0]


@db_session
def get_sample(area, dataset, number_of_samples, k=0, select_criteria=1, background=False, random_sample=False):
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
                                If the number_of_samples is a float in the range (0, 1), then that percentage of the
                                total population will be selected.
    :param k:                   The number of neighbors to each point we want to get.
    :param select_criteria:     Toggles how much information is to be selected for the point:
                                    1 -> Selects (id, long_lat) from point
                                    2 -> Selects (id, long_lat, region) from point
                                    3 -> Selects (id, long_lat, region, dataset.id) from point, and the dataset
                                           (combined with region)
                                    4 -> Selects (id, local_location, relative_location, long_lat) from point
                                    5 -> Selects (id, local_location, relative_location, long_lat, region) from point
                                    6 -> Selects (id, local_location, relative_location, long_lat, region, dataset.id)
                                            from point and the dataset (combined with region)
                                    7 -> Selects (id, local_location, relative_location, long_lat, name, region,
                                    dataset.id)
                                        from point and the dataset (combined with region)
                                    8 -> Selects (id, local_location, relative_location, long_lat, name, sub_name,
                                    region,
                                                dataset.id)
                                        from point and the dataset (combined with region)
                                If the mode is different from these, a warning will be issued, and
                                mode 1 will be selected.
                                NB: When mode 3, or 6 is NOT selected, the set will not be normalized!
                                Default is 1.
    :param background:          Toggles whether or not the returned set is from the actual region, or from the
                                'background' of that region, e.i. anything but that region.
    :param random_sample:       Toggles whether or not the sample is to be randomized or not. Default is not, as it is
                                expensive (at the moment).
    :type area:                 str
    :type dataset:              str | list of [str]
    :type number_of_samples:    int
    :type k:                    int
    :type select_criteria:      int
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
    select_sql = select_sql_point(select_criteria, __extended_point_table)
    if dataset != "":
        select_sql += ", dataset "
        dataset_sql = dataset_to_string(dataset)
    else:
        dataset_sql = ""

    # Define whether or not we are getting background
    if background:
        # Are we sampling the background or not?
        equal_operator = " != "
    else:
        equal_operator = " = "

    # Deals with the WHERE clause
    if 'WHERE' in select_sql:
        where_sql = " AND "
    else:
        where_sql = " WHERE "
    if not __extended_point_table:
        where_sql += "point.region = region.id AND region.name" + equal_operator + "'" + name + "'"
        if sub_name != "":
            where_sql += " AND region.sub_name" + equal_operator + "'" + sub_name + "'"
    else:
        where_sql += "name " + equal_operator + "'" + name + "'"
        if sub_name != "":
            where_sql += " AND sub_name " + equal_operator + "'" + sub_name + "'"

    # Do we select randomly?
    if isinstance(number_of_samples, float) and 0 < number_of_samples <= 1:
        if 'WHERE' in select_sql or 'WHERE' in where_sql:
            sample_sql = " AND"
        else:
            sample_sql = " WHERE"
        sample_sql += " random() <= " + str(number_of_samples)
    else:
        if random_sample:
            if USE_NAIVE_SAMPLING:
                order_by_sql = " ORDER BY random() "
            else:
                total_number_of_samples = get_total_number_of_samples()
                if 'WHERE' in select_sql or 'WHERE' in where_sql:
                    order_by_sql = " AND"
                else:
                    order_by_sql = " WHERE"
                order_by_sql += " random() <= " + str(number_of_samples / total_number_of_samples)
        else:
            order_by_sql = ""

        # Limits the outputs if necessary
        if number_of_samples > 0:
            limit_sql = " LIMIT " + str(number_of_samples)
        else:
            limit_sql = ""
        sample_sql = order_by_sql + limit_sql

    # Compile the SQL query
    sql = select_sql + where_sql + dataset_sql + sample_sql + ";"
    query = db.execute(sql)
    points = query_to_point_list(query, number_of_elements=number_of_samples, user_row_count=True)
    if k <= 0:
        return points
    else:
        return get_nearest_neighbor_to_points(points, k, dataset)
        # TODO: Add info about whether or not this is a target.


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


def _bands_to_column(point):
    """
    Takes a point, and converts the bands into an NumPy array (row)
    :param point:   A (Base)Point object from which we wish to extract the spectrum from.
    :type point:    BasePoint
    :return:        A row of floats representing the spectrum of the given point.
    :rtype:         np.array
    """
    bands = point.bands
    spectrum = np.array(bands)  # Converts the bands to a NumPy array
    # spectrum = spectrum.reshape(len(bands), 1)  # Transposes a row vector to a column vector
    return spectrum


def _neighbors_to_matrix(points):
    """
    Converts a list of points (neighbors) to a NumPy matrix, where each row corresponds to a point's spectrum.
    :param points:  The neighborhood/list of points we want to convert to a NumPy matrix.
    :type points:   list of [regions_of_interest.region.BasePoint]
    :return:        A NumPy matrix (array of array) where each row is a point's spectrum
    """
    return np.array([point.bands for point in points])


