# -*- coding: utf-8 -*-
"""
Classes and methods for reading, and interpreting the data from a ASCII ROI file.
"""
__author__ = 'Sindre Nistad'
import sys

from Common.common import get_histogram, extract_name, list_to_string
from Common.data_management import read_data_from_file, read_normalizing_data
from RegionOfInterest.region import ROI
from Common.common import strip_and_add_space, is_min_max, is_gaussian

if sys.version_info.major == 2:
    from cPickle import dump, load, HIGHEST_PROTOCOL
elif sys.version_info.major == 3:
    from pickle import dump, load, HIGHEST_PROTOCOL
else:
    Exception("Are you really using Python 1.x?!")


class RegionsOfInterest(object):
    """
        A holder/structure for the ROI file, as given by ENVI (in ASCII format)
    """
    def __init__(self, path, read_data=True, use_aggregate=True,
                 normalizing_path=None, mode='min-max', normalize=True, is_normalized=False):
        """
            Creates a RegionsOfInterest object, which is a collection of region on interest, each having a
            number of points in it. The default is to read the data at creation, and to use the aggregate
            name of the regions, e.g. 'rock' instead of 'rock_23'.
        :param path:                The path to either the ROI text file, or an already pickled RegionsOfInterest
                                    object.
        :param read_data:           Decides whether or not the data is to be read when the new RegionsOfInterest object
                                    is created. The default is to read at creation.
        :param use_aggregate:       Decides whether or not you can refer to a region by its general name,
                                    e.g. 'rock', or
                                    if you have to specify the entire name of the region e.g. 'rock_r43'. The default is
                                    to use the aggregate.
        :param normalizing_path:    The path to where the normalizing data is stored for the data set.
        :param mode:                The mode of how the data is to be normalized.
        :param normalize:           Toggles whether or not the data will be normalized. Default is True.
        :param is_normalized:       Specify whether or not the input data is normalized or not. The default is not.
        :type path:                 str
        :type read_data:            bool
        :type use_aggregate:        bool
        :type normalizing_path:     str
        :type mode:                 str
        :type normalize:            bool
        :type is_normalized:        bool
        """
        self.path = path
        """ :type : list of [str] """
        self.rois = {}
        """ :type : dict of [str, dict of [str, ROI]] """
        self.number_of_rois = 0
        """ :type : int """
        self.meta = ""
        """ :type : str """
        self.img_dim = []
        """ :type : list[int] """
        self.band_info = ""
        """ :type : list[str] """
        self.num_bands = 0
        """ :type : int"""
        self.histogram = None
        """ :type: dict of [str, int] """
        self.use_aggregate = use_aggregate
        """ :type : bool """
        self.is_normalized = is_normalized
        """ :type : bool """
        self.maximums = []
        """ :type : list[float] """
        self.minimums = []
        """ :type : list[float] """
        self.means = []
        """ :type : list[float] """
        self.standard_deviations = []
        """ :type : list[float] """
        self.is_loaded = False
        """ :type : bool """

        if read_data:
            ending = self.path.split('.')[-1]
            if ending == 'pkl' or ending == 'pickle':
                self.load_roi_object(path)
            else:
                self._load_data_from_file()
        if normalizing_path is not None:
            self._load_normalizing_data(normalizing_path, mode, normalize)

    def load_data(self):
        """
            Loads the data from the given path
        :return:    None
        :rtype:     None
        """
        self._load_data_from_file()
        self.is_loaded = True

    def _load_data_from_file(self):
        """
            Loads the region of interest data from the given file, and adds it to the fields of this object.
        :return:    None
        :rtype:     None
        """
        data = read_data_from_file(self.path)
        self.rois = data['rois']
        self.number_of_rois = data['number_of_rois']
        self.meta = data['meta']
        self.img_dim = data['img_dim']
        self.band_info = data['band_info']
        self.num_bands = data['num_bands']

    def _load_normalizing_data(self, path, mode, normalize=True):
        """
            Loads the data so that normalizing is possible, and then normalizes the data
        :param path:    The path to where the normalizing data is located
        :param mode:    What kind of normalizing should be done.
        :type path:     str
        :type mode:     str
        :return:        None
        :rtype:         None
        """
        data = read_normalizing_data(path)
        self.maximums = data['maximums']
        self.minimums = data['minimums']
        self.means = data['means']
        self.standard_deviations = data['standard_deviations']
        if normalize:
            self.normalize(mode)

    def load_roi_object(self, path):
        """
            Loads a pickled rois object into this one.
        :param path:    The path to the file you want to load.
        :return:        None
        """
        roi = load(open(path, 'rb'))
        assert isinstance(roi, RegionsOfInterest)
        self.path = roi.path
        self.rois = roi.rois
        self.number_of_rois = roi.number_of_rois
        self.meta = roi.meta
        self.img_dim = roi.img_dim
        self.band_info = roi.band_info
        self.num_bands = roi.num_bands
        self.use_aggregate = roi.use_aggregate
        self.is_normalized = roi.is_normalized

    def set_aggregate(self, val):
        """
            Sets the 'use_aggregate' filed to True, or False
        :param val:
        :type val: bool
        :return: None
        """
        assert isinstance(val, bool)
        self.use_aggregate = val

    def sort(self, mode):
        """
            Sorts all the regions of interest according to the give mode, which may be 'x-y', 'map', or 'lat-long'.
        :param mode:    What parameters do we sort on?
        :type mode:     str
        :return:        None
        :rtype:         None
        """
        for roi in self.rois:
            roi.sort(mode)

    def get_histogram(self):
        """
            Returns a dictionary of regions of interest, and how many points there is in each.
        :return:    Dictionary where the region of interest is the key, and the number of points
                    in that region is the value.
        :rtype:     dict of [str, int]
        """
        if self.histogram is None:
            targets = self.rois.keys()
            self.histogram = get_histogram(self.get_all(), targets)
        return self.histogram

    def save_to_file(self, filename):
        """
            Pickles the entire object to the specified file.
        :param filename:    The full name of the path/file name of the desired output file.
        :type filename:     str
        :return:            None
        :rtype:             None
        """
        with open(filename, 'wb') as output:
            dump(self, output, HIGHEST_PROTOCOL)

    def save_to_csv(self, delimiter=",", path=None):
        """
            Saves all the information to a CSV file. (Two, if the data is normalized: one for the 'raw' data, and one
            for the normalizing data.
        :param delimiter:   The delimiter to separate the data.
        :param path:        The path to where the CSV file is to be saved
        :type delimiter:    str
        :type path:         str
        :return:            None
        :rtype:             None
        """
        if path is None:
            path = self.path
            path = path.split(".")[0]
            path += ".csv"
        f = open(path, 'w')
        delimiter = strip_and_add_space(delimiter)
        label = "Name" + delimiter + "sub_name" + delimiter + \
                "Red" + delimiter + "Green" + delimiter + "Blue" + delimiter
        label += list_to_string(self.band_info, delimiter)
        f.write(label + '\n')
        for roi in self.get_all():
            f.write(roi.export_to_csv(return_val=True, delimiter=delimiter))
        f.close()
        if self.maximums is not None:
            f = open(path + '.norm.csv', 'w')
            meta = self.band_info[7:]
            description = "Value" + delimiter + list_to_string(meta, delimiter)
            description = description[:-2]  # Removes the last delimiter
            f.write(description + '\n')
            f.write("Maximum" + delimiter + list_to_string(self.maximums, delimiter) + '\n')
            f.write("Minimum" + delimiter + list_to_string(self.minimums, delimiter) + '\n')
            f.write("Mean" + delimiter + list_to_string(self.means, delimiter) + '\n')
            f.write("Standard deviation" + delimiter + list_to_string(self.standard_deviations, delimiter) + '\n')
            f.close()

    def normalize(self, mode='min-max'):
        """
            Normalizes the data. Makes it simpler than the original normalize function, which takes a subtraction, and
            and a division parameter.
            The mode can be 'min-max', or gaussian.
        :param mode:    Specify the way the data can be normalized. At the moment, only min-max,
                        and gaussian normalization is supported.
        :type mode:     str
        :return:        None
        :rtype:         None
        """
        if is_min_max(mode):
            assert self.minimums is not None
            assert self.maximums is not None
            self._normalize_min_max(self.minimums, self.maximums)
        elif is_gaussian(mode):
            assert self.means is not None
            assert self.standard_deviations is not None
            self._normalize_gaussian(self.means, self.standard_deviations)

    def _normalize_gaussian(self, mean_param, std_dev_param):
        """
            A method to normalize the rois, as to make it more portable between images.
            The parameters must be per band
            Per now, the modes of normalizing is globally, and only min-max, and gaussian.
        :param mean_param:      The mean value of the data set
        :param std_dev_param:   The standard deviation of the data set.
        :type mean_param:       list[float]
        :type std_dev_param:    list[float]
        :return: None
        :rtype: None
        """
        if not len(mean_param) == self.num_bands and len(std_dev_param) == self.num_bands:
            raise Exception("The input parameters does not match the bands in the ROIs")
        for roi in self.get_all():
            for point in roi.points:
                for i in range(self.num_bands):
                    point.bands[i] = (point.bands[i] - mean_param[i]) / std_dev_param[i]
        self.is_normalized = True

    def _normalize_min_max(self, min_param, max_param):
        """
            A method to normalize the rois, as to make it more portable between images.
            The parameters must be per band
            Per now, the modes of normalizing is globally, and only min-max, and gaussian.
        :param min_param:   The minimum value of the data set.
        :param max_param:   The maximum value of the data set.
        :type min_param:    list[float]
        :type max_param:    list[float]
        :return: None
        :rtype: None
        """
        if not len(min_param) == self.num_bands and len(max_param) == self.num_bands:
            raise Exception("The input parameters does not match the bands in the ROIs")
        for roi in self.get_all():
            for point in roi.points:
                for i in range(self.num_bands):
                    point.bands[i] = (point.bands[i] - min_param[i]) / (max_param[i] - min_param[i])
        self.is_normalized = True

    def absolutize(self, mode='min-max'):
        if mode == 'min-max' or mode == 'max-min':
            self._absolutize_min_max()
        elif mode == 'gaussian' or mode == 'gauss':
            self._abolutize_gaussian()
        else:
            raise NotImplementedError("Only min-max, and gaussian reversed normalize has been implemented")
        self.is_normalized = False

    def _absolutize_min_max(self):
        """
            Reverts what have been done when normalizing the data.
        :return:            None
        :rtype:             None
        """
        if not self.is_normalized:
            raise Exception("The data has to be normalized, if you want to revert the normalization!")
        for roi in self.rois:
            for point in roi.points:
                for i in range(self.num_bands):
                    point.bands[i] = point.bands[i] * (self.maximums[i] - self.minimums[i] ) + self.minimums[i]

    def _abolutize_gaussian(self):
        """
            Reverts what have been done when normalizing the data.
        :return:            None
        :rtype:             None
        """
        if not self.is_normalized:
            raise Exception("The data has to be normalized, if you want to revert the normalization!")
        for roi in self.rois:
            for point in roi.points:
                for i in range(self.num_bands):
                    point.bands[i] = point.bands[i] * self.standard_deviations[i] + self.means[i]

    def get_all(self, force_load=False):
        """
            A method to get all regions of interest as a list of regions
        :param force_load:  Toggles whether or not the data must be loaded if it is not already.
        :type force_load:   bool
        :return:            A list of the regions of interest that are stored in this object.
        :rtype:             List of [ROI]
        """
        if force_load and not self.is_loaded:
            self.load_data()
        roi_list = []
        for key in self.rois.keys():
            for sub_key in self.rois[key]:
                roi_list.append(self.rois[key][sub_key])
        return roi_list

    def __getitem__(self, item):
        if self.use_aggregate:
            rois = self.rois[item]
            points = []
            for key in rois.keys():
                roi = rois[key]
                color = roi.rgb
                points += roi.points
            return ROI(item, "", color, len(points), points)
        else:
            name, sub_name = extract_name(item)
            return self.rois[name][sub_name]

    def __len__(self):
        return len(self.rois)
