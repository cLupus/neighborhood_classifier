# -*- coding: utf-8 -*-

"""
    A file for handling all the loading, and moving of data
"""
from __future__ import division

__author__ = 'Sindre Nistad'

from random import random

from warnings import warn

from Common.common import get_neighbors
from Common.common import get_histogram, extract_name, split_numbers
from RegionOfInterest.region import Point, ROI

"""
Pre-process data
"""


def merge_roi_files(paths):
    """
        Method for merging different files together, assuming they are over the same area.
        :param paths:   A list of paths to files
        :type paths:    list of [str]
        :return:        Does not return anything, bu saves the merged data into a new file, called
                        merged_[file1]_[file2]_..._[filen].txt where [filei] is the name of the i-th file.
    """
    # Get the data from the files
    data = []
    for path in paths:
        # Read the regions of interest information from its file
        roi_data = read_data_from_file(path)
        # The dict of dict of region polygons with points
        rois = roi_data['rois']
        rois = convert_to_single_dict(rois)
        # Update the region of interest polygons
        roi_data['rois'] = rois
        data.append(roi_data)
    point_set = {}
    for roi_data in data:
        meta = roi_data['meta']
        """ :type : str """
        number_of_rois = roi_data['number_of_rois']
        """ :type : int """
        img_dim = roi_data['img_dim']
        """ :type : list[int] """
        band_info = roi_data['band_info']
        """ :type : list[str] """
        rois = roi_data['rois']
        """ :type : dict[str, ROI] """
        num_bands = roi_data['num_bands']
        """ :type : int """
        for key in rois.keys():
            roi = rois[key]
            for point in roi.points:
                # TODO: Have a boundary for what is considered close enough
                coord = "LA" + str(point.latitude) + "LO" + str(point.longitude)
                extended_point = {'meta': meta,
                                  'number_of_rois': number_of_rois,
                                  'img_dim': img_dim,
                                  'band_info': band_info,
                                  'num_bands': num_bands,
                                  'point': point
                                  }
                if coord in point_set:
                    point_set[coord].append(extended_point)
                else:
                    point_set[coord] = [extended_point]
    # TODO
    pass

"""
Read data from files
"""


def read_normalizing_data(path):
        """
            Reads a file with normalizing data for each band.
            The file is of the form:
            Maximum 'numbers'
            Minimum 'numbers'
            Means   'numbers'
            Std_dev 'numbers'
            Where 'numbers' is a list of numbers.
        :param path:    The path to the file which will be read
        :type path:     str
        :return:
        """
        data_file = open(path, 'r')
        maxs = _read(data_file, '\t')
        mins = _read(data_file, '\t')
        means = _read(data_file, '\t')
        std_dev = _read(data_file, '\t')

        data_file.close()
        # Removes the names
        maxs.pop(0)
        mins.pop(0)
        means.pop(0)
        std_dev.pop(0)

        data = {'maximums': split_numbers(maxs),
                'minimums': split_numbers(mins),
                'means': split_numbers(means),
                'standard_deviations': split_numbers(std_dev)
                }
        return data


def _read_meta_data(datafile):
        """
            A method to read the meta-data of the roi file, that is, read what kind of rois there are, how many
            points each roi has in it and so forth.
        :param datafile:    The data file to be read from
        :type datafile:     file
        :return:            A dictionary with the regions of interest, meta data, image dimensions, and more.
                            (Everything that was assigned to self earlier.)
        :rtype:             dict of [str, object]
        """
        rois = []  # a list for all the rois, so that the order is remembered.
        band_info = ""  # To make Python stop complaining, that it might be used before declared.
        # (If the file is as it should, it will always be assigned)

        meta = _read(datafile)  # We don't really need the information on the first line

        # Reads the second line of the file "; Number of ROIs: ?". We are interested in ?
        second_line = _read(datafile, '')
        number_of_rois = int(second_line[-1])

        # Reads the third line of the file "; File Dimension: ?? x ??"
        third_line = _read(datafile, '')
        img_dim = [int(third_line[-3]), int(third_line[-1])]

        # Reads an empty line
        _read(datafile)

        # Read the ROIs
        for i in range(number_of_rois):
            # Read the name of te ROI
            name_string = _read(datafile)
            roi_name, roi_sub_name = extract_name(name_string)

            # Read the RGB value of the region (in the form "{r, g, b}")
            roi_rgb_string = _read(datafile, '')  # Results in ['{r,', 'g,', 'b}']
            red = roi_rgb_string[-3][1]
            green = roi_rgb_string[-2][0]
            blue = roi_rgb_string[-1][0]
            colors = [red, green, blue]
            roi_rgb = split_numbers(colors)

            # Reads the number of points there are in that region
            roi_points_string = _read(datafile, '')
            roi_points = int(roi_points_string[-1])

            rois.append(ROI(roi_name, roi_sub_name, roi_rgb, roi_points))

            # Makes sure the band information is kept.
            if i == number_of_rois - 1:
                # Extracts the different fields, including 'map X', and 'map Y', but not the beginning ';'
                meta_string = datafile.readline()
                band_info = [item.strip() for item in meta_string.split("  ") if item.strip() and item != ';']
            else:
                _read(datafile)  # Reads an empty line
        # A dictionary that will store all the details
        result = {'meta': meta,
                  'number_of_rois': number_of_rois,
                  'img_dim': img_dim,
                  'band_info': band_info,
                  'rois': rois}
        return result


def _read_spectral_data(datafile, results):
        """
            A method that read the spectral data from the file, and adds it to the result dictionary, which is then
             processed by the region of interest.
        :param datafile:    The file from which we read the (spectral) data.
        :param results:     The results containing the meta data, and the dictionary to which we add the spectral data.
        :type datafile:     file
        :type results:      dict of [str, object]
        :return:            The results dictionary with the added spectral data.
        :rtype:             dict of [str, object]
        """
        rois = results['rois']
        res_rois = {}
        for roi in rois:
            for i in range(roi.num_points):
                line = datafile.readline()
                while line == "" or line == '\n' or line == '\r\n':
                    line = datafile.readline()
                specter_string = line
                specter_string = specter_string.split()
                spectrum = [float(x) for x in specter_string]
                identity = int(spectrum[0])
                x = int(spectrum[1])
                y = int(spectrum[2])
                map_x = spectrum[3]
                map_y = spectrum[4]
                latitude = spectrum[5]
                longitude = spectrum[6]
                bands = spectrum[7:]
                point = Point(identity, x, y, map_x, map_y, latitude, longitude, bands)
                roi.add_point(point)

            if roi.name in res_rois:
                res_rois[roi.name][roi.sub_name] = roi
            else:
                res_rois[roi.name] = {}
                res_rois[roi.name][roi.sub_name] = roi
        results['num_bands'] = len(bands)
        results['rois'] = res_rois
        return results


def read_data_from_file(path, send_residuals=False):
    """
        An aggregate method for reading the data from a file, and returning a dictionary of the information:
        'meta',
        'number_of_rois',
        'img_dim',
        'band_info',
        'rois', and
        'num_bands'
        are the keys.
    :param path:            The path to the file we want to read from
    :param send_residuals:  Toggles whether or not the rest of the file will be sent back. For debugging.
    :type path:             str
    :type send_residuals:   bool
    :return:                A dictionary with all the information from the regions of interest.
    :rtype:                 dict of [str, str |
                            list of [float] |
                            int |
                            list of [int] |
                            dict of [str, dict of [str, ROI]]]
    """
    data_file = open(path, 'r')
    results = _read_meta_data(data_file)
    results = _read_spectral_data(data_file, results)
    if send_residuals:
        results['residuals'] = data_file.readlines()
    data_file.close()
    return results


def _read(data_file, delimiter=None):
    """
        Helper method for reading data from file, and cleaning it up.
    :param data_file:   The file from which we which to read.
    :param delimiter:   The delimiter for which to split the string. The default is to not split the string.
    :type data_file:    file
    :type delimiter:    str
    :return:            A cleaned up string.
    :rtype:             str | list of [str]
    """
    data = data_file.readline()
    if delimiter is not (None or ''):
        return [d.strip() for d in data.split(delimiter)]
    elif delimiter is '':
        return [d.strip() for d in data.split()]
    else:
        return data.strip()

"""
Load data
Primarily for loading data from a regions of interest object to a data set.
"""


def _load_limited_data(roi_obj, data_set, targets, neighborhood_size, targets_background_ratio):
    """
        A helper method for load_dataset to load the data when considering a sub-selection. If a ratio is negative,
        it will be interpreted as zero probability.
    :param roi_obj:                     The ROI object
    :param targets:                     The list of targets (may contain only one + background)
    :param neighborhood_size:           The diameter of the neighborhood
    :param targets_background_ratio:    Specify the ratio of the number target pixels to the number of
                                        background pixels. The default is to not use it, but it can be useful when
                                        num targets <<< num background. It is per target excluding background.

    :type roi_obj:                      RegionsOfInterest
    :type targets:                      list[str]
    :type neighborhood_size:            int
    :type targets_background_ratio:     list of [float] | dict of [str, float]
    :return:                            A data set sorting all the points of the regions of interest according to
                                        'target' and 'background'.
    :rtype:                             ClassificationDataSet
    """
    assert len(targets) == len(targets_background_ratio)  # Just in case...

    if not isinstance(targets_background_ratio, dict):
        # The input is lists, but we want
        targets_to_background = _convert_to_dict(targets, targets_background_ratio)
    else:
        targets_to_background = targets_background_ratio

    # Determine the distribution of the data set.
    orig_histogram = get_histogram(roi_obj.get_all(), targets)
    feasible_sizes = _find_feasible_sizes(roi_obj, targets_to_background)

    # Determining the appropriate probabilities for selection.
    background_probability = feasible_sizes['background'] / orig_histogram['background']
    probabilities = {'background': background_probability}
    for target in targets:
        if target.lower() != 'background':  # For simplicity
            # FIXME: the probability adjustment is incorrect...
            prob = targets_to_background[target] / background_probability
            if prob > 1:
                probabilities[target] = 1
            elif prob > 0:
                probabilities[target] = prob
            else:
                probabilities[target] = 0
    return _add_samples_to_data_set(roi_obj.get_all(), targets, data_set, neighborhood_size, probabilities)


def _load_regular_data(roi_obj, data_set, targets, neighborhood_size):
    """
        A helper method for load_dataset to load all the data from a RegionsOfInterest object
    :param roi_obj:                     The ROI object
    :param targets:                     The list of targets (may contain only one + background)
    :param neighborhood_size:           The diameter of the neighborhood

    :type roi_obj:                      RegionsOfInterest
    :type targets:                      list[str]
    :type neighborhood_size:            int
    :return:                            A data set sorting all the points of the regions of interest according to
                                        'target' and 'background'.
    :rtype:                             ClassificationDataSet
    """
    for roi in roi_obj.get_all():
        if roi.name not in targets:
            name = 'background'
        else:
            name = roi.name
        add_points_to_sample(roi, data_set, name, neighborhood_size)
    return data_set


def _add_samples_to_data_set(roi_list, targets, data_set, neighborhood_size, probabilities=None):
    """
        A helper method to add the points of the regions of interest to a data set, according to some probability
        distribution, which is by default disabled: probability of 1 for the points to be added.
    :param roi_list:            A list of region of interest objects.
    :param targets:             A list of targets, including the 'background' target.
    :param data_set:            The data set to which the points are to be added.
    :param neighborhood_size:   The 'diameter' of the neigborhood.
    :param probabilities:       A list (or dictionary) of probabilities specifying the probabilities of target
                                number i is added to the data set. The default is None, specifying that all
                                targets will be added.
    :return:                    If count is set to False, the function returns the data set.
                                If count is set to True, the function returns a dictionary of targets (including
                                'background') that has the frequency of each target.

    :type roi_list:             list[ROI]
    :type targets:              list[str]
    :type data_set:             ClassificationDataSet
    :type neighborhood_size:    int
    :type probabilities:        list[float] | dict of [str, float]
    :rtype:                     ClassificationDataSet
    """
    target_dict = {}  # This because ClassificationDataSet require the number of a target, as opposed to the name.
    probability_dict = {}  # For convenience.

    # If we are to use probabilities, they must be the same size as the targets.
    if probabilities is not None:
        assert len(probabilities) == len(targets)
    for i in range(len(targets)):
        target = targets[i]
        target_dict[target] = i
        if probabilities is None:
            probability_dict[target] = 1
        elif isinstance(probabilities, dict):
            probability_dict = probabilities
        else:
            prob = probabilities[i]
            probability_dict[target] = prob

    for roi in roi_list:
        if roi.name is 'background' or roi.name not in targets:
            number = target_dict['background']
            prob = probability_dict['background']
            add_points_to_sample(roi, data_set, number, neighborhood_size, prob)
        else:  # The ROI is a target
            number = target_dict[roi.name]
            prob = probability_dict[roi.name]
            add_points_to_sample(roi, data_set, number, neighborhood_size, prob)
    return data_set


"""
Auxiliary
"""


def add_points_to_sample(roi, data_set, target, neighborhood_size, probability=1):
    """
        Adds all the points in a region of interest to a data set, accounting for neighborhood.
    :param roi:                 The region of interest.
    :param data_set:            The data set to which the points will be added.
    :param target:              The name of the target
    :param neighborhood_size:   The size along the axis
    :param probability:         The probability that a point will be added to the list.

    :type roi:                  ROI
    :type data_set:             ClassificationDataSet
    :type target:               str
    :type neighborhood_size:    int
    :type probability:          float
    :return:                    None
    :rtype:                     None
    """
    # Making sure the probability is reasonable.
    # With the current implementation, this is unnecessary...
    if probability > 1:
        probability = 1
    elif probability < 0:
        probability = 0

    for point in roi.points:
        if probability <= random():
            continue
        else:
            neighborhood_list = get_neighbors(point, roi.points, neighborhood_size, True)
            bands = [p.bands if p is not None else [0 for _ in range(len(point.bands))] for p in neighborhood_list]
            collected_bands = []
            for band in bands:
                collected_bands += band
            data_set.addSample(collected_bands, target)


def _convert_to_dict(strings, objects):
    """
        Converts the the set of strings and objects to a dictionary of the form {strings[0]: objects[0],
        strings[1]: objects[1], ..., strings[n]: objects[n]}, where n is the last element of the set.
    :param strings:     A list of strings that will act as the key for each entry.
    :param objects:     A list of objects that will be the corresponding item.
    :return:            A dictionary with key/values from the two lists.

    :type strings:      list of [str]
    :type objects:      list of [object]
    :rtype:             dict of [str, object]
    """
    assert len(strings) == len(objects)
    res = {}
    for i in range(len(strings)):
        res[strings[i]] = objects[i]
    return res


def _find_feasible_sizes(roi_obj, targets_background_ratio):
    """
        A helper method to determine the expected sizes of the different targets.
    :param roi_obj:                     A RegionsOfInterest object, so that all the the distribution of
                                        points can be determined.
    :param targets_background_ratio:    The desired ratios of number of points for each target relative to the
                                        points of background pixels.
    :return:                            Returns a dictionary of integers describing the number points we would
                                        like to have of each target.

    :type roi_obj:                      RegionsOfInterest
    :type targets_background_ratio:     dict of [str, float]
    :rtype:                             dict of [str, int]
    """
    roi_list = roi_obj.get_all()
    histogram = get_histogram(roi_list, targets_background_ratio, count_points=True)
    num_pixels = {}
    keys = histogram.keys()
    background_pixels = []
    for key in keys:
        background_pixels.append(int(histogram[key] / targets_background_ratio[key]))
    target_background_pixels = min(background_pixels)
    for key in keys:
        num_pixels[key] = int(targets_background_ratio[key] * target_background_pixels)
    for key in keys:
        if num_pixels[key] / num_pixels['background'] != targets_background_ratio[key]:
            warn("Warning:\nThe given targets to background ratios does not seem to be feasible, or possible, "
                 "so the effective ratios have been changed to some that work, and are close to the given ratios: "
                 "The minimum possible number of background pixels, and the given ratios. \nContinuing.")
            break
    return num_pixels


def convert_to_single_dict(rois):
    """
        Converts a dictionary of dictionary to a single dictionary.
    :param rois:    The dictionary of dictionaries.
    :type rois:     dict of [str, dict of [str, object]]
    :return:        A single dictionary of the concatenated keys of the two dictionaries.
    :rtype:         dict of [str, object]
    """
    result = {}
    for key in rois.keys():
        roi = rois[key]
        for sub_key in roi.keys():
            result[key + "_" + sub_key] = roi[sub_key]
    return result