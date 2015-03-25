# -*- coding: utf-8 -*-

"""
    A file for handling all the loading, and moving of data
"""
from __future__ import division

__author__ = 'Sindre Nistad'

from random import random

from warnings import warn

from pybrain.datasets import ClassificationDataSet

from regions_of_interest import RegionsOfInterest
from common import get_histogram

"""
Loads data
"""


def load_data_set_from_regions_of_interest(roi_obj, targets, neigborhood_size,
                                           targets_background_ratios=None, have_background=True):
    """
        A method that loads the data set from a RegionsOfInterest object, to a ClassificationDataSet.
        Only the relevant targets needs to be specified, as background will be added automatically.
    :param roi_obj:                     The ROI object
    :param targets:                     The list of targets (may contain only one + background)
    :param neigborhood_size:            The diameter of the neigborhood
    :param targets_background_ratios:   Specify the ratio of the number target pixels to the number of
                                        background pixels. The default is to not use it, but it can be useful when
                                        num targets <<< num background. It is per target excluding background.
    :param have_background:             Toggles whether or not we are to use a background class. Default is yes.

    :type roi_obj:                      RegionsOfInterest
    :type targets:                      list[str]
    :type neigborhood_size:             int
    :type targets_background_ratios:    list of [float] | dict of [str, float]
    :type have_background:              bool
    :return:                            A data set sorting all the points of the regions of interest according to
                                        'target' and 'background'.
    :rtype:                             ClassificationDataSet
    """

    if have_background:
        targets.append('background')

    data_set = ClassificationDataSet(neigborhood_size ** 2 * roi_obj.num_bands,
                                     2,
                                     nb_classes=len(targets),
                                     class_labels=targets)
    if targets_background_ratios is not None:
        assert len(targets) == len(targets_background_ratios)
        return _load_limited_data(roi_obj, data_set, targets, neigborhood_size, targets_background_ratios)
    else:
        return _load_regular_data(roi_obj, data_set, targets, neigborhood_size)


def _load_limited_data(roi_obj, data_set, targets, neigborhood_size, targets_background_ratio):
    """
        A helper method for load_dataset to load the data when considering a sub-selection. If a ratio is negative,
        it will be interpreted as zero probability.
    :param roi_obj:                     The ROI object
    :param targets:                     The list of targets (may contain only one + background)
    :param neigborhood_size:            The diameter of the neigborhood
    :param targets_background_ratio:    Specify the ratio of the number target pixels to the number of
                                        background pixels. The default is to not use it, but it can be useful when
                                        num targets <<< num background. It is per target excluding background.

    :type roi_obj:                      RegionsOfInterest
    :type targets:                      list[str]
    :type neigborhood_size:             int
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
            prob = background_probability * targets_to_background[target]
            if prob > 1:
                probabilities[target] = 1
            elif prob > 0:
                probabilities[target] = prob
            else:
                probabilities[target] = 0
    return _add_samples_to_data_set(roi_obj.get_all(), targets, data_set, neigborhood_size, probabilities)


def _load_regular_data(roi_obj, data_set, targets, neigborhood_size):
    """
        A helper method for load_dataset to load all the data from a RegionsOfInterest object
    :param roi_obj:                     The ROI object
    :param targets:                     The list of targets (may contain only one + background)
    :param neigborhood_size:            The diameter of the neigborhood

    :type roi_obj:                      RegionsOfInterest
    :type targets:                      list[str]
    :type neigborhood_size:             int
    :return:                            A data set sorting all the points of the regions of interest according to
                                        'target' and 'background'.
    :rtype:                             ClassificationDataSet
    """
    for roi in roi_obj.get_all():
        if roi.name not in targets:
            name = 'background'
        else:
            name = roi.name
        add_points_to_sample(roi, data_set, name, neigborhood_size)
    return data_set


def _add_samples_to_data_set(roi_list, targets, data_set, neigborhood_size, probabilities=None):
    """
        A helper method to add the points of the regions of interest to a data set, according to some probability
        distribution, which is by default disabled: probability of 1 for the points to be added.
    :param roi_list:            A list of region of interest objects.
    :param targets:             A list of targets, including the 'background' target.
    :param data_set:            The data set to which the points are to be added.
    :param neigborhood_size:    The 'diameter' of the neigborhood.
    :param probabilities:       A list (or dictionary) of probabilities specifying the probabilities of target
                                number i is added to the data set. The default is None, specifying that all
                                targets will be added.
    :return:                    If count is set to False, the function returns the data set.
                                If count is set to True, the function returns a dictionary of targets (including
                                'background') that has the frequency of each target.

    :type roi_list:             list[ROI]
    :type targets:              list[str]
    :type data_set:             ClassificationDataSet
    :type neigborhood_size:     int
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
            if random() <= prob:
                add_points_to_sample(roi, data_set, number, neigborhood_size)
        else:  # The ROI is a target
            number = target_dict[roi.name]
            prob = probability_dict[roi.name]
            if random() <= prob:
                add_points_to_sample(roi, data_set, number, neigborhood_size)
    return data_set


"""
Auxiliary
"""


def add_points_to_sample(roi, data_set, target, neighborhood_size):
    """
        Adds all the points in a region of interest to a data set, accounting for neighborhood.
    :param roi:                 The region of interest.
    :param data_set:            The data set to which the points will be added.
    :param target:              The name of the target
    :param neighborhood_size:   The size along the axis
    :type roi:                  ROI
    :type data_set:             ClassificationDataSet
    :type target:               str
    :type neighborhood_size:    int
    :return:                    None
    :rtype:                     None
    """
    for point in roi.points:
        neighborhood_list = roi.get_neighbors(point, neighborhood_size, True)
        bands = [p.bands if p is not None else [0 for _ in xrange(len(point.bands))] for p in neighborhood_list]
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
    for i in xrange(len(strings)):
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