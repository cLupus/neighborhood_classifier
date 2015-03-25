# -*- coding: utf-8 -*-
__author__ = 'Sindre Nistad'

from warnings import warn
from cPickle import dump, load, HIGHEST_PROTOCOL
from random import random

from pybrain.datasets import ClassificationDataSet
from pybrain.tools.shortcuts import buildNetwork
from pybrain.structure.modules import SoftmaxLayer, TanhLayer
from pybrain.structure import FeedForwardNetwork
from pybrain.supervised.trainers import BackpropTrainer
from pybrain.tools.xml import NetworkReader, NetworkWriter

from regions_of_interest import RegionsOfInterest, ROI
from common import get_index


class ClassificationNet():
    """
        A
    """

    def __init__(self,
                 rois,
                 targets,
                 neigborhood_size=1,
                 target_background=True,
                 targets_background_ration=None,
                 hidden_layer=-1,
                 output_layer=1,
                 split_proportion=-1,
                 set_trainer=False):
        """
            Initializes a neural network for classification.
        :param rois:                        A RegionsOfInterest object containing the ROIs
        :param targets:                     A list of strings with the target(s)
        :param neigborhood_size:            The size (diameter in pixels) of the neigborhood the
                                            neural network considers.
        :param target_background:           Toggles mode: if true, then we are only interested in classifying ONE
                                            target, and then consider all the other targets as background.
                                            If false, the net will try to classify every target.
        :param targets_background_ration:   A list of target to background ratios; how much background should there
                                            in relation to target pixels. The default is to disable it.
        :param hidden_layer:                The number of input layers to the network. The default is to have half
                                            as many as there is input nodes and output nodes.
        :param output_layer:                The number of output layers. The default is 1
        :param split_proportion:            Defines how large a proportion will be given to as training data, and
                                            test/validation data. The proportion says what proportion will be used
                                            as test data. The default is to not split the data.
        :param set_trainer:                 Toggles whether or not the trainer should be created immediately or not.
                                            The default is yes.
        :type rois:                         RegionsOfInterest
        :type targets:                      list[str]
        :type target_background:            bool
        :type targets_background_ration:    list of [float]
        :type neigborhood_size:             int
        :type hidden_layer:                 int
        :type output_layer:                 int
        :type split_proportion:             float
        :type set_trainer:                  bool
        :return:
        """
        if neigborhood_size % 2 == 0:
            warn("The size of the neigborhood should be an odd number! Continuing")
        input_layers = neigborhood_size ** 2 * rois.num_bands
        if hidden_layer < 0:
            hidden_layer = int((input_layers + output_layer)/2)

        self.target_background = target_background
        """ :type : bool """
        self.targets = targets
        """ :type : list of [str] """
        self.neigborhood_size = neigborhood_size
        """ :type : int """
        self.neural_net = build_net(input_layers, hidden_layer, output_layer)
        """ :type : FeedForwardNetwork """
        self.data_set = load_dataset(rois, targets, neigborhood_size,
                                     targets_background_ratios=targets_background_ration,
                                     have_background=target_background)
        """ :type : ClassificationDataSet """
        self.trainer = None
        """ :type : BackpropTrainer """
        self.validation_data = None
        """ :type : ClassificationDataSet """
        self.training_data = None
        """ :type : ClassificationDataSet """
        self.is_normalized = rois.is_normalized
        """ :type : bool """
        self.num_bands = rois.num_bands
        """ :type : int """
        if 0 <= split_proportion < 1:
            self.split_data(split_proportion)
        if set_trainer:
            self.set_trainer()

    def split_data(self, proportion=0.5):
        """
            A helper method to split the data into a validation set, and a training set.
        :param proportion:  The proportion of validation to training data.
        :type proportion:   float
        :return: None
        """
        self.validation_data, self.training_data = self.data_set.splitWithProportion(proportion)
        self.validation_data._convertToOneOfMany()  # Because PyBrain's documentation recommends doing so.
        self.training_data._convertToOneOfMany()

    def set_trainer(self, learning_rate=0.01, lrdecay=1.0,
                    momentum=0., verbose=False, batch_learning=False,
                    weight_decay=0.):
        """
            Sets the trainer. If the data has been split, it uses the training data as data for the back-propagation
            algorithm. If not, it uses the entire data set.
        :param learning_rate:       The rate in which the parameters are changed into the direction of the gradient.
        :param lrdecay:             How much the learning rate decreases per epoch. Multiplicative!
        :param momentum:            The weight of the previous time-step's gradient is affecting the next iteration.
        :param verbose:             Toggles verbose mode. Default is off.
        :param batch_learning:      Will be parameters be updated at the end of the epoch, or continuously? The default
                                    is continuously.
        :param weight_decay:        How much the weighs are decreasing. 0 corresponds to no decrease.
        :type learning_rate:        float
        :type lrdecay:              float
        :type momentum:             float
        :type verbose:              bool
        :type batch_learning:       bool
        :type weight_decay:         float
        :return: None
        """
        if self.training_data is not None:
            self.trainer = BackpropTrainer(self.neural_net, self.training_data,
                                           learning_rate, lrdecay, momentum, verbose,
                                           batch_learning, weight_decay)
        else:
            self.trainer = BackpropTrainer(self.neural_net, self.training_data,
                                           learning_rate, lrdecay, momentum, verbose,
                                           batch_learning, weight_decay)

    def train_network(self,
                      max_epochs=-1,
                      verbose=False,
                      continue_epochs=10,
                      validation_proportion=0.25,
                      force_split=False):
        """
            Trains the network until the error rate converges.
        :param max_epochs:              The maximum number of epochs the network is trained. The default is to not set a
                                        maximum.
        :param verbose:                 Toggles verbose mode or not. The default is not.
        :param continue_epochs:         How much longer the training should go on if we find a minimum in the error.
        :param validation_proportion:   The proportion that will be used for validation. The default is 25%, given that
                                        the 'self.validation_data' has not been set.
        :param force_split:             If the 'self.validation_data' as been set, we can force another split on the
                                        training data.
        :type max_epochs:               int
        :type verbose:                  bool
        :type continue_epochs:          int
        :type validation_proportion:    float
        :type force_split:              bool
        :return:                        None
        """
        if max_epochs <= 0:
            # We don't give it a stop criteria for time.
            if self.validation_data is not None:
                # We have already set aside some of the data for validation
                if force_split:
                    # Screw that! I want the data to be split again!
                    self.trainer.trainUntilConvergence(self.training_data, None, verbose,
                                                       continue_epochs, validation_proportion)
                else:
                    self.trainer.trainUntilConvergence(self.training_data, None, verbose, continue_epochs, 1)
            else:
                # We have no validation data set
                self.trainer.trainUntilConvergence(self.data_set, None, verbose, continue_epochs, validation_proportion)
        else:
            # We have a stop criteria.
            if self.validation_data is not None:
                # We have already split the data into a validation set, and a training set.
                if force_split:
                    # Screw that! I want the data to be split again
                    self.trainer.trainUntilConvergence(self.training_data, max_epochs, verbose,
                                                       continue_epochs, validation_proportion)
                else:
                    self.trainer.trainUntilConvergence(self.training_data, max_epochs, verbose, continue_epochs, 1)
            else:
                # We do not have a validation data set.
                self.trainer.trainUntilConvergence(self.data_set, max_epochs, verbose,
                                                   continue_epochs, validation_proportion)

    def set_target(self, target):
        pass

    def save(self, path):
        """
            Saves the current state of the neural network to the file specified.
            If the ending is .pkl, or .pickle, the whole object will be dumped as a pickle file.
            If the ending is .xml, or .nn, or .neural.net, then PyBrain's NetworkWriter will be used.
            If the ending is .data, or .training.data, or .validation.data, then all the data, training data,
            or the validation data will be saved.
        :param path:    The path to where the file where the neural network will be saved.
        :type path:     str
        :return:
        """
        splited_path = path.split('.')
        ending = splited_path[-1]
        sub_ending = splited_path[-2]
        if ending is ('pkl' or 'pickle'):
            with open(path, 'wb') as handle:
                dump(self, handle, HIGHEST_PROTOCOL)
        elif ending is ('xml' or 'nn') or (ending is 'net' and sub_ending is 'neural'):
            NetworkWriter.writeToFile(self.neural_net, path)
        elif ending is 'data':
            if sub_ending is 'training':
                with open(path, 'wb') as handle:
                    dump(self.training_data, handle, HIGHEST_PROTOCOL)
            elif sub_ending is 'validation':
                with open(path, 'wb') as handle:
                    dump(self.validation_data, handle, HIGHEST_PROTOCOL)
            else:
                with open(path, 'wb') as handle:
                    dump(self.data_set, handle, HIGHEST_PROTOCOL)

    def load(self, path):
        """
            Loads the pickled file in to the object
        :param path:    The path, or file name for the pickled/save file.
        :type path:     str
        :return:        None
        :rtype:         None
        """
        splited_path = path.split('.')
        ending = splited_path[-1]
        sub_ending = splited_path[-2]
        if ending is ('pkl' or 'pickle'):
            with open(path, 'rb') as handle:
                net = load(handle)
            assert isinstance(net, ClassificationNet)
            self.target_background = net.target_background
            self.targets = net.targets
            self.neigborhood_size = net.neigborhood_size
            self.neural_net = net.neigborhood_size
            self.data_set = net.data_set
            self.is_normalized = net.is_normalized
            self.num_bands = net.num_bands
        elif ending is ('xml' or 'nn') or (ending is 'net' and sub_ending is 'neural'):
            net = NetworkReader.readFrom(path)
            assert isinstance(net, FeedForwardNetwork)
            self.neural_net = net
        elif ending is 'data':
            if sub_ending is 'training':
                with open(path, 'rb') as handle:
                    training_data = load(handle)
                assert isinstance(training_data, ClassificationDataSet)
                self.training_data = training_data
            elif sub_ending is 'validation':
                with open(path, 'rb') as handle:
                    validation_data = load(handle)
                assert isinstance(validation_data, ClassificationNet)
                self.validation_data = validation_data

    def apply_to_image(self, img, normalized_img=False):
        """
            A method to apply the neural network classifier to an entire image.
        :param img:             Image to be classified.
        :param normalized_img:  A flag to indicate that the image has been normalized. The default is to
                                assume that the image has not been normalized.
        :type img:              list of [list of [list of [float | int]]]
        :type normalized_img:   bool
        :return:                A classified image of the same size, as well as a list of targets corresponding to
                                the values of the classification.
        :rtype                  list of [list of [int]], list of [str]
        """
        if not self.is_normalized or not normalized_img:
            warn("The image, and the neural network should be normalized for portability. Continuing.")
        cols = len(img)
        rows = len(img[0])
        bands = len(img[0][0])
        if bands != self.num_bands:
            raise Exception("The number of bands in the image does not match the number of bands in the neural net",
                            (bands, self.num_bands))
        classified_img = [[0 for _ in xrange(rows)] for _ in xrange(cols)]  # Creates an empty image for classification.
        buffer_size = int(self.neigborhood_size/2)  # To avoid out of range errors.
        for row in xrange(buffer_size, rows - buffer_size):
            for col in xrange(buffer_size, cols - buffer_size):
                neigborhood = get_neigborhood(img, row, col, self.neigborhood_size)
                classified_img[col][row] = self.neural_net.activate()


def get_neigborhood(img, row, col, neigborhood_size, concatenated=True):
    """
        A method to get all the bands in the neigborhood of a pixel, and concatenate it into a single list of numbers
    :param img:                 The image from which the neigborhood is to be extracted.
    :param row:                 The row of the pixel we are interested in.
    :param col:                 The column of the pixel we are interested in.
    :param neigborhood_size:    The size of the neigborhood of the pixel.
    :param concatenated:        Toggles whether or not we return a single list, or a list per pixel in the neigborhood.
                                The default is to return a single list.
    :type img:                  list of [list of [list of [float | int]]]
    :type row:                  int
    :type col:                  int
    :type neigborhood_size:     int
    :type concatenated:         bool
    :return:                    If the concatenated option is set to True,  we return a single list of numbers.
                                If the concatenated option is set to False, we return a list for each pixel.
    :rtype:                     list of [list of [int | float]] | list of [list of [list of [int | float]]]
    """
    if concatenated:
        neigborhood = [None for _ in xrange(neigborhood_size ** 2)]
    else:
        neigborhood = [[None for _ in xrange(neigborhood_size)] for _ in xrange(neigborhood_size)]
    min_x = row - int(neigborhood_size / 2)
    min_y = col - int(neigborhood_size / 2)
    cols = len(img)
    rows = len(img[0])
    for i in xrange(neigborhood_size):
        for j in xrange(neigborhood_size):
            bands = img[col - min_y + j][row - min_x + i]
            if concatenated:
                index = get_index(rows, i, cols, j, neigborhood_size)
                neigborhood[index] = bands
            else:
                neigborhood[i][j] = bands
    return neigborhood


def build_net(indim, hiddendim, outdim):
    """
        Creates a neural network for classification
    :param indim:       The number of input nodes
    :param hiddendim:   The number of nodes in the hidden layer
    :param outdim:      The number of nodes in the output layer
    :type indim:        int
    :type hiddendim:    int
    :type outdim:       int
    :return:            A neural network with random weights.
    :rtype:             FeedForwardNetwork
    """
    return buildNetwork(indim, hiddendim, outdim, outclass=SoftmaxLayer, hiddenclass=TanhLayer)


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


def _find_desired_size(roi_obj, targets_background_ratio):
    """
        A helper method to determine the expected sizes of the different targets.
    :param roi_obj:                     A RegionsOfInterest object, so that all the the distribution of
                                        points can be determined.
    :param targets_background_ratio:    The desired ratios of number of points for each target relative to the
                                        points of background pixels.
    :return:                            Returns a list of integers describing the number points we would like to
                                        have of each target.

    :type roi_obj:                      RegionsOfInterest
    :type targets_background_ratio:     dict of [str, float]
    """
    roi_list = roi_obj.get_all()
    histogram = _count_or_add(roi_list, targets_background_ratio, count=True, count_points=True)
    num_backgrounds = []
    for key in histogram.keys():
        background_pixels = histogram[key] / targets_background_ratio
    pass


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


def _load_limited_data(roi_obj, data_set, targets, neigborhood_size, targets_background_ratio):
    """
        A helper method for load_dataset to load the data when considering a sub-selection.
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
    assert len(targets) == len(targets_background_ratio)
    targets_to_background = _convert_to_dict(targets, targets_background_ratio)
    desiered_size = _find_desired_size(roi_obj, targets_to_background)
    pass


def load_dataset(roi_obj, targets, neigborhood_size, targets_background_ratios=None, have_background=True):
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
    :rtype:                     dict of [str, int] | ClassificationDataSet
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


def _histogram(roi_list, targets,  count_points=True):
    """
        A helper method to count the distribution of the targets.
    :param roi_list:            A list of region of interest objects.
    :param targets:             A list of targets, including the 'background' target.
    :param count_points:        Toggles whether or not to count each point, or each ROI as a unit of the count mode.
    :return:                    If count is set to False, the function returns the data set.
                                If count is set to True, the function returns a dictionary of targets (including
                                'background') that has the frequency of each target.

    :type roi_list:             list[ROI]
    :type targets:              list[str]
    :type count_points:         bool
    :rtype:                     dict of [str, int] | ClassificationDataSet
    """
    count_data = {}

    for roi in roi_list:
        if roi.name is 'background' or roi.name not in targets:
            if count_points:
                count_data['background'] += roi.num_points
            else:
                count_data['background'] += 1
        else:  # The ROI is a target
            if count_points:
                count_data[roi.name] += roi.num_points
            else:
                count_data['background'] += 1
    return count_data


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

