__author__ = 'Sindre Nistad'


class RegionsOfInterest:


    def __init__(self, path):

        self.roi_file = open(path)
        self.rois = {}
        self.number_of_rois = 0
        self.meta = ""
        self.img_dim = []
        self.band_info = ""


    def read_data(self, send_residuals=False):
        temp_rois = self._read_meta_data()
        self._read_spectral_data(temp_rois)
        if send_residuals:
            return self.roi_file.readlines()
        self.roi_file.close()


    def _read_meta_data(self):
        """
            A method to read the meta-data of the roi file, that is, read what kind of rois there are, how many
            points each roi has in it and so forth.
        :return rois:   returns a list of rois that are ordered according to when they were read, as to make
                        the reading of the actual points easier
        """
        rois = [] # a list for all the rois, so that the order is remembered.

        self.meta = self.roi_file.readline()  # We don't really need the information on the first line

        # Reads the second line of the file "; Number of ROIs: ?". We are interested in ?
        second_line = self.roi_file.readline()
        second_line = second_line.split()
        self.number_of_rois = int(second_line[-1])

        # Reads the third line of the file "; File Dimension: ?? x ??"
        third_line = self.roi_file.readline()
        third_line = third_line.split()
        self.img_dim = [ int(third_line[-3]), int(third_line[-1]) ]


        # Reads an empty line
        self.roi_file.readline()

        # Read the ROIs
        for i in xrange(self.number_of_rois):
            # Read the name of te ROI
            roi_name_string = self.roi_file.readline()
            roi_name_string = roi_name_string.split()
            roi_name = roi_name_string[-1]

            # Read the RGB value of the region (in the form "{r, g, b}")
            roi_rgb_string = self.roi_file.readline()
            roi_rgb_string = roi_rgb_string.split()  # Results in ['{r,', 'g,', 'b}']
            red = roi_rgb_string[-3]
            green = roi_rgb_string[-2]
            blue = roi_rgb_string[-1]
            colors = [red, green, blue]
            roi_rgb = _split_numbers(colors)

            # Reads the number of points there are in that region
            roi_points_string = self.roi_file.readline()
            roi_points_string = roi_points_string.split()
            roi_points = int(roi_points_string[-1])

            rois.append(ROI(roi_name, roi_rgb, roi_points))

            # Makes sure the band information is kept.
            if i == self.number_of_rois - 1:
                self.band_info = self.roi_file.readline().split()
                self.band_info.pop(0)
            else:
                self.roi_file.readline()  # Reads an empty line
        return rois


    def _read_spectral_data(self, rois):
        """
            A method that reads, and adds all the spectral data into the program
        :param rois: a list of ROIs
        :type rois: list[ROI]
        :return : void
        """

        for roi in rois:
            for i in xrange(roi.num_points):
                specter_string = self.roi_file.readline()
                specter_string = specter_string.split()
                spectrum = [float(x) for x in specter_string]
                #spectrum = map(float, specter_string)  # Splits the string of numbers, and converts it to float
                identity = spectrum[0]
                x = spectrum[1]
                y = spectrum[2]
                map_x = spectrum[3]
                map_y = spectrum[4]
                latitude = spectrum[5]
                longitude = spectrum[6]
                bands = spectrum[7:-1]
                point = Point(identity, x, y, map_x, map_y, latitude, longitude, bands)
                roi.add_point(point)

            self.rois[roi.name] = roi
            self.roi_file.readline()  # Reads the empty line between the ROIs




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

    def __init__(self, name, rgb, num_points):
        """
            A object to hold the information on a region of interest.
        :param name:
        :param rgb:
        :param num_points:

        :type name: string
        :type rgb: list[int]
        :type num_points: int

        :return:
        """
        self.name = name
        self.rgb = rgb
        self.num_points = num_points
        self.points = []

    def add_point(self, point):
        self.points.append(point)


class Point():

    def __init__(self, identity, x, y, map_x, map_y, latitude, longitude, bands):
        self.identity = identity
        self.X = x
        self.Y = y
        self.map_X = map_x
        self.map_Y = map_y
        self.latitude = latitude
        self.longitude = longitude
        self.bands = bands
