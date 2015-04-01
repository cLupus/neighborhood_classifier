# -*- coding: utf-8 -*-
"""
Classes and methods for reading, and interpreting the data from a ASCII ROI file.
"""
__author__ = 'Sindre Nistad'

from cPickle import dump, load, HIGHEST_PROTOCOL

from Auxiliary.common import get_histogram, extract_name, ROI
from Auxiliary.data_management import read_data_from_file, read_normalizing_data


class RegionsOfInterest(object):
    """
        A holder/structure for the ROI file, as given by ENVI (in ASCII format)
    """
    def __init__(self, path, read_data=True, use_aggregate=True,
                 normalizing_path=None, mode='min-max', is_normalized=False):
        """
            Creates a RegionsOfInterest object, which is a collection of region on interest, each having a
            number of points in it. The default is to read the data at creation, and to use the aggregate
            name of the regions, e.g. 'rock' instead of 'rock_23'.
        :param path:            The path to either the ROI text file, or an already pickled RegionsOfInterest object.
        :param read_data:       Decides whether or not the data is to be read when the new RegionsOfInterest object
                                is created. The default is to read at creation.
        :param use_aggregate:   Decides whether or not you can refer to a region by its general name, e.g. 'rock', or
                                if you have to specify the entire name of the region e.g. 'rock_r43'. The default is
                                to use the aggregate.
        :param is_normalized:   Specify whether or not the input data is normalized or not. The default is not.
        :type path:             str
        :type read_data:        bool
        :type use_aggregate:    bool
        :type is_normalized:    bool
        """
        self.path = path
        """ :type : str """
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

        if read_data:
            ending = self.path.split('.')[-1]
            if ending == 'pkl' or ending == 'pickle':
                self.load_roi_object(self.path)
            else:
                data = read_data_from_file(self.path)
                self.rois = data['rois']
                self.number_of_rois = data['number_of_rois']
                self.meta = data['meta']
                self.img_dim = data['img_dim']
                self.band_info = data['band_info']
                self.num_bands = data['num_bands']
        if normalizing_path is not None:
            data = read_normalizing_data(normalizing_path)
            self.maximums = data['maximums']
            self.minimums = data['minimums']
            self.means = data['means']
            self.standard_deviations = data['standard_deviations']
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

    def get_histogram(self):
        if self.histogram is None:
            targets = self.rois.keys()
            self.histogram = get_histogram(self.get_all(), targets)
        return self.histogram

    def save_to_file(self, filename):
        with open(filename, 'wb') as output:
            dump(self, output, HIGHEST_PROTOCOL)

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
        if mode is 'min-max' or 'max-min':
            assert self.minimums is not None
            assert self.maximums is not None
            self._normalize(self.minimums, self.maximums)
        elif mode is 'gaussian' or 'gauss':
            assert self.means is not None
            assert self.standard_deviations is not None
            self._normalize(self.means, self.standard_deviations)

    def _normalize(self, sub_param, div_param):
        """
            A method to normalize the rois, as to make it more portable between images.
            The parameters must be per band
            Per now, the modes of normalizing is globally, and only min-max, and gaussian.
        :param sub_param:   The parameter that is subtracted from the value, e.g. minimum, or mean.
        :param div_param:   The parameter that divides the subtracted value, e.g. maximum, or std.dev.
        :type sub_param:    list[float]
        :type div_param:    list[float]
        :return: None
        :rtype: None
        """
        if not len(sub_param) == self.num_bands and len(div_param) == self.num_bands:
            raise Exception("The input parameters does not match the bands in the ROIs")
        for roi in self.get_all():
            for point in roi.points:
                for i in range(self.num_bands):
                    point.bands[i] = (point.bands[i] - sub_param[i]) / div_param[i]
        self.is_normalized = True

    def absolutize(self, sub_param, div_param, mode='min-max'):
        """
            Reverts what have been done when normalizing the data.
        :param sub_param:   The parameter that was subtracted when the data was normalized, e.g. minimum, or mean
        :param div_param:   The parameter that was used to divide the data, when it was normalized, e.g. maximum,
                            or std.dev.
        :param mode:        How the reversion should be done.
        :type sub_param:    list[float]
        :type div_param:    list[float]
        :type mode:         str
        :return:            None
        :rtype:             None
        """
        if not self.is_normalized:
            raise Exception("The data has to be normalized, if you want to revert the normalization!")
        for roi in self.rois:
            for point in roi.points:
                for i in range(self.num_bands):
                    point.bands[i] = point.bands[i] * div_param[i] + sub_param[i]

    def get_all(self):
        """
            A method to get all regions of interest as a list of regions
            :return:    A list of the regions of interest that are stored in this object.
            :rtype:     List of [ROI]
        """
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

