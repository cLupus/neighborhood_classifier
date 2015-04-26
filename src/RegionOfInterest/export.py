# -*- coding: utf-8 -*-
"""
Misc. functions for exporting, and importing data to the different structures used in this project.
"""
from __future__ import division

from RegionOfInterest.regions_of_interest import RegionsOfInterest
from Database.connector import roi_to_database

__author__ = 'Sindre Nistad'


def get_file_list(normalized=False):
    """

    :param normalized:
    :return:
    """
    master = ['master_r19_7_5_emissivity_sub']
    aviris = ['sb_r19_sub_sub_corrected', 'sb_r20_2011_rfl_sub',
              'sb_r21_sub_sub_corrected', 'sb_r22_sub_sub_corrected_colored']
    aviris_extension = '.aviris'
    targets = master
    targets.extend([a + aviris_extension for a in aviris])
    extension = '.txt'
    prefix = '/Users/sindrenistad/Dropbox/workspace/geog214a/neighborhood_classifier/ASCII roi/'
    norm = 'normalizing/'
    if normalized:
        return ["".join([prefix, norm, itm, extension]) for itm in targets]
    else:
        return ["".join([prefix, itm, extension]) for itm in targets]


def get_all_rois(normalized=True, read_data=False):
    """
        Makes all the regions of interest from the different files, and returns them in a list
    :param normalized:  Toggles whether or not the output is normalized or not. Default is True.
    :param read_data:   Toggles whether or not the data will be loaded at creation or not.
    :type normalized:   bool
    :type read_data:    bool
    :return:            All the regions of interest that are given by the files.
    :rtype:             list of [RegionsOfInterest]
    """
    files = get_file_list()
    normalized_file = get_file_list(True)
    return [
        RegionsOfInterest(files[i],
                          normalizing_path=normalized_file[i],
                          normalize=normalized,
                          read_data=read_data)
        for i in range(len(files))
    ]


def get_roi(i, normalized=False):
    """
        Get a single set of regions of interest (e.g. the MASTER set)
    :param i:           The index in the fileset (which regions of interest)
    :param normalized:  Is the set to be normalized? Default is False
    :return:            A single RegionsOfInterest object
    :rtype:             RegionsOfInterest
    """
    files = get_file_list()
    normalized_file = get_file_list(True)
    return RegionsOfInterest(files[i], normalizing_path=normalized_file[i], normalize=normalized)


def export_to_pickle():
    """
        Exports all the rois to their own pickled file
    :return:    Nothing, but the files.
    :rtype:     None
    """
    rois = get_all_rois()
    for roi in rois:
        print("Now processing " + roi.path)
        # Gets the original file-name without the extension
        name = roi.path.split("/")[-1].split(".")[0]
        roi.save_to_file("".join([name, ".pkl"]))


def export_to_csv(delimiter=",", normalized=True):
    """
        Exports all the rois to CSV
    :param delimiter:   The delimiter to be used. Default is ','
    :param normalized:  Toggles whether or not the rois will be normalized, or not. Default is True.
    :type delimiter:    str
    :type normalized:   bool
    :return:            Does not return anything, but creates csv files.
    :rtype:             None
    """
    rois = get_all_rois(normalized=normalized)
    for roi in rois:
        roi.save_to_csv(delimiter)


def export_to_potgres(add_wavelengths=False, debug=False):
    if debug:
        n = len(get_all_rois(read_data=False))
        i = 0
    for roi in get_all_rois(read_data=False):
        print("Now loading the dataset located at " + roi.path)
        roi.load_data()
        print("Loading complete. Now exporting to database.")
        roi_to_database(roi, add_wavelengths=add_wavelengths, debug=debug)
        if debug:
            i += 1
            print("NOW " + str(i / n * 100) + "% COMPLETE")
        print("Data committed to the database.")
        print("Deleting region to save memory; these files can be huge")
        del roi

    # TODO: Implement
    pass
