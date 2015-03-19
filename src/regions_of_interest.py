__author__ = 'Sindre Nistad'

from re import split as regex_split
from cPickle import dump, load, HIGHEST_PROTOCOL


class RegionsOfInterest:

    def __init__(self, path):
        """
        :type path: str
        """
        self.path = path
        self.rois = {}
        self.number_of_rois = 0
        self.meta = ""
        self.img_dim = []
        self.band_info = ""
        self.num_bands = 0
        self.use_aggregate = False
        self.is_normalized = False

        # :type path: str
        # :type rois: dict of [dict of [ROI]]
        # :type number_of_rois: int
        # :type meta: str
        # :type img_dim: list[int]
        # :type band_info: list[str]
        # :type num_bands: int
        # :type use_aggregate: bool
        # :type is_normalized: bool

    def load_roi_object(self, path):
        roi = load(open(path, 'rb'))
        assert isinstance(roi, RegionsOfInterest)
        self.path = roi.path
        self.rois = roi.rois
        self.number_of_rois = roi.number_of_rois
        self.meta = roi.meta
        self.img_dim = roi.img_dim
        self.band_info = roi.band_info
        self.use_aggregate = roi.use_aggregate

    def set_aggregate(self, val):
        """

        :param val:
        :type val: bool
        :return:
        """
        self.use_aggregate = val

    def read_data(self, send_residuals=False):
        """
            An aggregate method for reading the data.
        :param send_residuals:
        :type send_residuals: bool
        :return:
        """
        # The inputfile is a pickle file, and we want to load the file instead of reading data
        if self.path.split(".")[-1] == 'pkl':
            self.load_roi_object(self.path)
        else:
            datafile = open(self.path, 'r')
            temp_rois = self._read_meta_data(datafile)
            self._read_spectral_data(temp_rois, datafile)
            if send_residuals:
                return datafile.readlines()
            datafile.close()

    def _read_meta_data(self, datafile):
        """
            A method to read the meta-data of the roi file, that is, read what kind of rois there are, how many
            points each roi has in it and so forth.
        :param datafile: The data file to be read from
        :return rois:   returns a list of rois that are ordered according to when they were read, as to make
                        the reading of the actual points easier
        """
        rois = []  # a list for all the rois, so that the order is remembered.

        self.meta = datafile.readline()  # We don't really need the information on the first line

        # Reads the second line of the file "; Number of ROIs: ?". We are interested in ?
        second_line = datafile.readline()
        second_line = second_line.split()
        self.number_of_rois = int(second_line[-1])

        # Reads the third line of the file "; File Dimension: ?? x ??"
        third_line = datafile.readline()
        third_line = third_line.split()
        self.img_dim = [ int(third_line[-3]), int(third_line[-1]) ]


        # Reads an empty line
        datafile.readline()

        # Read the ROIs
        for i in xrange(self.number_of_rois):
            # Read the name of te ROI
            name_string = datafile.readline()
            roi_name, roi_sub_name = _extract_name(name_string)


            # Read the RGB value of the region (in the form "{r, g, b}")
            roi_rgb_string = datafile.readline()
            roi_rgb_string = roi_rgb_string.split()  # Results in ['{r,', 'g,', 'b}']
            red = roi_rgb_string[-3]
            green = roi_rgb_string[-2]
            blue = roi_rgb_string[-1]
            colors = [red, green, blue]
            roi_rgb = _split_numbers(colors)

            # Reads the number of points there are in that region
            roi_points_string = datafile.readline()
            roi_points_string = roi_points_string.split()
            roi_points = int(roi_points_string[-1])

            rois.append(ROI(roi_name, roi_sub_name, roi_rgb, roi_points))

            # Makes sure the band information is kept.
            if i == self.number_of_rois - 1:
                # Extracts the different fields, including 'map X', and 'map Y', but not the beginning ';'
                meta_string = datafile.readline()
                self.band_info = [meta.strip() for meta in meta_string.split("  ") if meta.strip() and meta != ';']

            else:
                datafile.readline()  # Reads an empty line
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
                identity = spectrum[0]
                x = spectrum[1]
                y = spectrum[2]
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


def _extract_name(name_string):
    """
        A helper method to extract the name of the ROI, and separate it into main name, and part name
    :param name_string: The full string of the line with the name
    :type name_string: str
    :return: the first name of the region, and the sub name of the region
    """
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


def _split_numbers(numbers):
    """
        A subroutine to extract the numbers from the list of strings
    :param numbers:
    :type numbers: list[string]
    :return :
    """

    res = []
    for elm in numbers:
        res.append(int(filter(str.isdigit, elm)))

    return res


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

    def get_neighbor(self, point, num_neighbors):
        """
            A method that gets the n neighbors of a point (and the point itself) in a matrix
        :param point: The ROI Point of interest
        :param num_neighbors: The diameter of the neighborhood

        :type point: Point
        :type num_neighbors: int
        :rtype: list[list[Point]]
        :return: Matrix of Points corresponding to the neighborhood. Some of the points ma
        """
        points = [[None for _ in xrange(num_neighbors)] for _ in xrange(num_neighbors)]
        x = point.X
        y = point.Y
        max_x = x + int(num_neighbors/2)
        min_x = x - int(num_neighbors/2)
        max_y = y + int(num_neighbors/2)
        min_y = y - int(num_neighbors/2)
        for p in self.points:
            if min_x <= p.X <= max_x and min_y <= p.Y <= max_y:
                index_x, index_y = get_index(max_x, p.X, max_y, p.Y, num_neighbors)
                points[index_y][index_x] = p
        return points

    def __len__(self):
        return len(self.points)


def get_index(max_x, x, max_y, y, num_neighbors):
    return num_neighbors - (max_x - x), num_neighbors - (max_y - y)


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
