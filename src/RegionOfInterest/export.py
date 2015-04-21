__author__ = 'Sindre Nistad'

from RegionOfInterest.regions_of_interest import RegionsOfInterest


def get_file_list(normalized=False):
    """

    :param normalized:
    :return:
    """
    targets = ['master_r19_7_5_emissivity_sub', 'sb_r19_sub_sub_corrected', 'sb_r20_2011_rfl_sub',
               'sb_r21_sub_sub_corrected', 'sb_r22_sub_sub_corrected_colored']
    #prefix = '/Volumes/Kingston/Geog214a_data/ASCII roi/'
    extension = '.txt'
    prefix = '/Users/sindrenistad/Dropbox/workspace/geog214a/neighborhood_classifier/ASCII roi/'
    # prefix = '../ASCII roi/'
    norm = 'normalizing/'
    if normalized:
        return ["".join([prefix, norm, itm, extension]) for itm in targets]
    else:
        return ["".join([prefix, itm, extension]) for itm in targets]


def get_all_rois(normalized=True):
    """
        Makes all the regions of interest from the different files, and returns them in a list
    :param normalized:  Toggles whether or not the output is normalized or not. Default is True.
    :type normalized:   bool
    :return:            All the regions of interest that are given by the files.
    :rtype:             list of [RegionsOfInterest]
    """
    files = get_file_list()
    normalized_file = get_file_list(True)
    return [RegionsOfInterest(files[i], normalizing_path=normalized_file[i], ) for i in range(len(files))]


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
    rois = get_all_rois(normalized=normalized)
    for roi in rois:
        roi.save_to_csv(delimiter)