# -*- coding: utf-8 -*-
__author__ = 'Sindre Nistad'

from re import split as regex_split
from cPickle import dump, load, HIGHEST_PROTOCOL

from common import get_indices, split_numbers, get_histogram


class RegionsOfInterest:

    def __init__(self, path, read_data=True, use_aggregate=True, is_normalized=False):
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
        self.maxs = []
        """ :type : list[float] """
        self.mins = []
        """ :type : list[float] """
        self.means = []
        """ :type : list[float] """
        self.std_devs = []
        """ :type : list[float] """

        if read_data:
            self.read_data()

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

    def read_data(self, send_residuals=False):
        """
            An aggregate method for reading the data.
        :param send_residuals:
        :type send_residuals: bool
        :return:
        """
        # TODO: Read data from different sources, and merge the data.
        # The input file is a pickle file, and we want to load the file instead of reading data
        if self.path.split(".")[-1] == 'pkl':
            self.load_roi_object(self.path)
        else:
            datafile = open(self.path, 'r')
            temp_rois = self._read_meta_data(datafile)
            self._read_spectral_data(temp_rois, datafile)
            if send_residuals:
                return datafile.readlines()
            datafile.close()

    def read_normalizing_data(self, path):
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
        self.maxs = split_numbers(maxs)
        self.mins = split_numbers(mins)
        self.means = split_numbers(means)
        self.std_devs = split_numbers(std_dev)

    def get_histogram(self):
        if self.histogram is None:
            targets = self.rois.keys()
            self.histogram = get_histogram(self.get_all(), targets)
        return self.histogram

    def _read_meta_data(self, datafile):
        """
            A method to read the meta-data of the roi file, that is, read what kind of rois there are, how many
            points each roi has in it and so forth.
        :param datafile: The data file to be read from
        :return rois:   returns a list of rois that are ordered according to when they were read, as to make
                        the reading of the actual points easier
        """
        rois = []  # a list for all the rois, so that the order is remembered.

        self.meta = _read(datafile, '')  # We don't really need the information on the first line

        # Reads the second line of the file "; Number of ROIs: ?". We are interested in ?
        second_line = _read(datafile, '')
        self.number_of_rois = int(second_line[-1])

        # Reads the third line of the file "; File Dimension: ?? x ??"
        third_line = _read(datafile, '')
        self.img_dim = [int(third_line[-3]), int(third_line[-1])]

        # Reads an empty line
        _read(datafile)

        # Read the ROIs
        for i in xrange(self.number_of_rois):
            # Read the name of te ROI
            name_string = _read(datafile)
            roi_name, roi_sub_name = _extract_name(name_string)

            # Read the RGB value of the region (in the form "{r, g, b}")
            roi_rgb_string = _read(datafile, '')  # Results in ['{r,', 'g,', 'b}']
            red = roi_rgb_string[-3]
            green = roi_rgb_string[-2]
            blue = roi_rgb_string[-1]
            colors = [red, green, blue]
            roi_rgb = split_numbers(colors)

            # Reads the number of points there are in that region
            roi_points_string = _read(datafile, '')
            roi_points = int(roi_points_string[-1])

            rois.append(ROI(roi_name, roi_sub_name, roi_rgb, roi_points))

            # Makes sure the band information is kept.
            if i == self.number_of_rois - 1:
                # Extracts the different fields, including 'map X', and 'map Y', but not the beginning ';'
                meta_string = datafile.readline()
                self.band_info = [meta.strip() for meta in meta_string.split("  ") if meta.strip() and meta != ';']
            else:
                _read(datafile)  # Reads an empty line
        return rois

    def _read_spectral_data(self, rois, datafile):
        """
            A method that reads, and adds all the spectral data into the program
        :param rois: a list of ROIs
        :type rois: list[ROI]
        :return : void
        """

        for roi in rois:
            for i in xrange(roi.num_points):
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

            if roi.name in self.rois:
                self.rois[roi.name][roi.sub_name] = roi
            else:
                self.rois[roi.name] = {}
                self.rois[roi.name][roi.sub_name] = roi
        self.num_bands = len(bands)

    def save_to_file(self, filename):
        with open(filename, 'wb') as output:
            dump(self, output, HIGHEST_PROTOCOL)

    def normalize(self, sub_param, div_param, mode='min-max'):
        """
            A method to normalize the rois, as to make it more portable between images.
            The parameters must be per band
            Per now, the modes of normalizing is globally, and only min-max, and gaussian.
        :param sub_param:   The parameter that is subtracted from the value, e.g. minimum, or mean.
        :param div_param:   The parameter that divides the subtracted value, e.g. maximum, or std.dev.
        :param mode:        How the normalization is done.
        :type sub_param:    list[float]
        :type div_param:    list[float]
        :type mode:         str
        :return: None
        :rtype: None
        """
        if not len(sub_param) == self.num_bands and len(div_param) == self.num_bands:
            raise Exception("The input parameters does not match the bands in the ROIs")
        for roi in self.rois:
            for point in roi.points:
                for i in xrange(self.num_bands):
                    point.bands[i] = (point.bands[i] - sub_param[i])/div_param[i]
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
                for i in xrange(self.num_bands):
                    point.bands[i] = point.bands[i] * div_param[i] + sub_param[i]

    def get_all(self):
        roi_list = []
        for key in self.rois.keys():
            for sub_key in self.rois[key]:
                roi_list.append(self.rois[key][sub_key])
        return roi_list

    def __getitem__(self, item):
        if self.use_aggregate:
            rois = self.rois[item]
            points = []
            color = [0, 0, 0]  # TODO: Get a color from the rois
            for key in rois.keys():
                roi = rois[key]
                points += roi.points
            return ROI(item, "", color, len(points), points)
        else:
            name, sub_name = _extract_name(item)
            return self.rois[name][sub_name]

    def __len__(self):
        return len(self.rois)


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


def _extract_name(name_string):
    """
        A helper method to extract the name of the ROI, and separate it into main name, and part name
    :param name_string: The full string of the line with the name
    :type name_string: str | list of [str]
    :return: the first name of the region, and the sub name of the region
    """
    if isinstance(name_string, str):
        name_string = name_string.split()
    full_name = name_string[-1]
    full_name = full_name.split('_')
    if len(full_name) > 1:  # e.i. the name is in the form name_region
        roi_name = full_name[0]
        sub_name = full_name[1]
    else:
        full_name = regex_split('(\d+)', full_name[0])
        roi_name = full_name[0]
        sub_name = full_name[1]
    return roi_name, sub_name


class ROI:

    def __init__(self, name, sub_name, rgb, num_points, points=None):
        """
            A object to hold the information on a region of interest.
        :param name:
        :param rgb:
        :param num_points:
        :param points:

        :type name: str
        :type rgb: list[int]
        :type num_points: int
        :type points: list[Point]

        :return:
        """
        self.name = name
        self.sub_name = sub_name
        self.rgb = rgb
        self.num_points = num_points
        if points is None:
            self.points = []
        else:
            self.points = points

    def add_point(self, point):
        self.points.append(point)

    def get_neighbors(self, point, num_neighbors, use_list=False):
        """
            A method that gets the n neighbors of a point (and the point itself) in a matrix
        :param point:           The ROI Point of interest
        :param num_neighbors:   The diameter of the neighborhood
        :param use_list:        Toggles whether or not the function is to return a list instead of a matrix

        :type point: Point
        :type num_neighbors: int
        :rtype: list[list[Point]] or list[Point]
        :return: Matrix of Points corresponding to the neighborhood. Some of the points ma
        """
        if not use_list:
            points = [[None for _ in xrange(num_neighbors)] for _ in xrange(num_neighbors)]
        else:
            points = [None for _ in xrange(num_neighbors ** 2)]

        x = point.X
        y = point.Y
        max_x = x + int(num_neighbors/2)
        min_x = x - int(num_neighbors/2)
        max_y = y + int(num_neighbors/2)
        min_y = y - int(num_neighbors/2)
        for p in self.points:
            if min_x <= p.X <= max_x and min_y <= p.Y <= max_y:
                index_x, index_y = get_indices(max_x, p.X, max_y, p.Y, num_neighbors)
                if not use_list:
                    points[index_y][index_x] = p
                else:
                    points[index_y * num_neighbors + index_x] = p
        return points

    def __len__(self):
        return len(self.points)


class Point():

    def __init__(self, identity, x, y, map_x, map_y, latitude, longitude, bands):
        """
            A object to hold, and organize the relevant information for a specific point in the data set.
        :param identity:    An id, unique to the ROI polygon at creation in ENVI. Not used
        :param x:           The (absolute) x location in the original image.
        :param y:           The (absolute) y location in the original image.
        :param map_x:       The x coordinate in the map.
        :param map_y:       The y coordinate in the map.
        :param latitude:    The absolute latitude of the point.
        :param longitude:   The absolute longitude of the point.
        :param bands:       A list of the different spectral bands for the point.
        :type identity:     int
        :type x:            int
        :type y:            int
        :type map_x:        float
        :type map_y:        float
        :type latitude:     float
        :type longitude:    float
        :type bands:        list[float]
        :return:
        """
        self.identity = int(identity)
        self.X = int(x)
        self.Y = int(y)
        self.map_X = map_x
        self.map_Y = map_y
        self.latitude = latitude
        self.longitude = longitude
        self.bands = bands

    def __len__(self):
        return len(self.bands)
