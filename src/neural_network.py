__author__ = 'Sindre Nistad'

from warnings import warn
from pybrain.datasets import ClassificationDataSet
from pybrain.tools.shortcuts import buildNetwork
from pybrain.structure.modules import SoftmaxLayer
from pybrain.structure import FeedForwardNetwork
from pybrain.supervised.trainers import BackpropTrainer
from pybrain.tools.xml import NetworkReader, NetworkWriter
from regions_of_interest import RegionsOfInterest, ROI
from cPickle import dump, load, HIGHEST_PROTOCOL
from random import random


class ClassificationNet():
    """
        A
    """

    def __init__(self,
                 rois,
                 targets,
                 neigborhood_size=1,
                 target_background=True,
                 hidden_layer=-1,
                 output_layer=1,
                 split_proportion=-1,
                 set_trainer=True):
        """
            Initializes a neural network for classification.
        :param rois:                A RegionsOfInterest object containing the ROIs
        :param targets:             A list of strings with the target(s)
        :param neigborhood_size:    The size (diameter in pixels) of the neigborhood the neural network considers.
        :param target_background:   Toggles mode: if true, then we are only interested in classifying ONE target, and
                                    then consider all the other targets as background. If false, the net will try to
                                    classify every target.
        :param hidden_layer:        The number of input layers to the network. The default is to have half as many as
                                    there is input nodes and output nodes.
        :param output_layer:        The number of output layers. The default is 1
        :param split_proportion:    Defines how large a proportion will be given to as training data, and
                                    test/validation data. The proportion says what proportion will be used as test data.
                                    The default is to not split the data.
        :param set_trainer:         Toggles whether or not the trainer should be created immediately or not.
                                    The default is yes.
        :type rois:                 RegionsOfInterest
        :type targets:              list[str]
        :type target_background:    bool
        :type neigborhood_size:     int
        :type hidden_layer:         int
        :type output_layer:         int
        :type split_proportion:     float
        :type set_trainer:          bool
        :return:
        """
        if neigborhood_size % 2 == 0:
            warn("The size of the neigborhood should be an odd number! Continuing")
        input_layers = neigborhood_size ** 2 * rois.num_bands
        if hidden_layer < 0:
            hidden_layer = int((input_layers + output_layer)/2)

        self.target_background = target_background
        """ :type : bool """
        self.num_targets = targets
        """ :type : int """
        self.neigborhood_size = neigborhood_size
        """ :type : int"""
        self.neural_net = build_net(input_layers, hidden_layer, output_layer)
        """ :type : FeedForwardNetwork """
        self.data_set = load_dataset(rois, targets, neigborhood_size, have_background=target_background)
        """ :type : ClassificationDataSet """
        self.trainer = None
        """ :type : BackpropTrainer """
        self.validation_data = None
        """ :type : ClassificationDataSet """
        self.training_data = None
        """ :type : ClassificationDataSet """
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
            self.num_targets = net.num_targets
            self.neigborhood_size = net.neigborhood_size
            self.neural_net = net.neigborhood_size
            self.data_set = net.data_set
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
    return buildNetwork(indim, hiddendim, outdim, outclass=SoftmaxLayer)


def load_dataset(roi_obj, targets, neigborhood_size, targets_background_ratio=None, have_background=True):
    """
        A method that loads the data set from a RegionsOfInterest object, to a ClassificationDataSet.
        Only the relevant targets needs to be specified, as background will be added automatically.
    :param roi_obj:                     The ROI object
    :param targets:                     The list of targets (may contain only one + background)
    :param neigborhood_size:            The diameter of the neigborhood
    :param targets_background_ratio:    Specify the ratio of the number target pixels to the number of
                                        background pixels. The default is to not use it, but it can be useful when
                                        num targets <<< num background. It is per target excluding background.
    :param have_background:             Toggles whether or not we are to use a background class. Default is yes.

    :type roi_obj:                      RegionsOfInterest
    :type targets:                      list[str]
    :type neigborhood_size:             int
    :type targets_background_ratio:     list of [float] | dict of [str, float]
    :type have_background:              bool
    :return:                            A data set sorting all the points of the regions of interest according to
                                        'target' and 'background'.
    :rtype:                             ClassificationDataSet
    """
    num_bands = len(roi_obj[targets[0]].points[0].bands)

    if have_background:
        targets.append('background')

    data_set = ClassificationDataSet(neigborhood_size ** 2 * num_bands,
                                     nb_classes=len(targets),
                                     class_labels=targets)
    roi_list = roi_obj.get_all()

    probabilities = None
    if targets_background_ratio is not None:
        if not isinstance(targets_background_ratio, dict):
            if 'background' in targets:
                n = len(targets) - 1
            else:
                n = len(targets)
            tmp = {}
            for i in range(n):
                tmp[targets[i]] = targets_background_ratio[i]
            targets_background_ratio = tmp
        probabilities = {}
        target_count = _count_or_add(roi_list, targets, count=True)
        background_count = float(target_count['background'])
        for key in target_count.keys():
            target_background_ratio = target_count[key] / background_count
            desiered_ratio = targets_background_ratio[key]
            if desiered_ratio > 1:
                # TODO
                # We want more targets than background
                probabilities['background'] = target_background_ratio / desiered_ratio
            else:
                # TODO
                probabilities[key] = target_background_ratio * desiered_ratio
            pass
    # Add points to the data set
    return _count_or_add(roi_list, targets, data_set, neigborhood_size, probabilities)


def _count_or_add(roi_list, targets, data_set=None, neigborhood_size=0, probabilities=None, count=False):
    """
        A helper method to either count the number of targets vs background, or add them to the data set.
    :param roi_list:            A list of region of interest objects.
    :param targets:             A list of targets, including the 'background' target.
    :param data_set:            The data set to which the points are to be added iff count is set to True.
    :param neigborhood_size:    The 'diameter' of the neigborhood. The default is zero; no points added.
    :param probabilities:       A list (or dictionary) of probabilities specifying the probabilities of target
                                number i is added to the data set. The default is None, specifying that all
                                targets will be added.
    :param count:               Toggles the mode of the function: To count the number of targets and background, or to
                                add the points to the data set.
    :return:                    If count is set to False, the function returns the data set.
                                If count is set to True, the function returns a dictionary of targets (including
                                'background') that has the frequency of each target.

    :type roi_list:             list[ROI]
    :type targets:              list[str]
    :type data_set:             ClassificationDataSet
    :type neigborhood_size:     int
    :type probabilities:        list[float] | dict of [str, float]
    :type count:                bool
    :rtype:                     dict of [str, int] | ClassificationDataSet
    """
    target_dict = {}  # This because ClassificationDataSet require the number of a target, as opposed to the name.
    probability_dict = {}  # For convenience.
    count_data = {}
    if count:
        # initialize the dictionary.
        for target in targets:
            count_data[target] = 0

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
            if not count:
                number = target_dict['background']
                prob = probability_dict['background']
                if random() <= prob:
                    add_points_to_sample(roi, data_set, number, neigborhood_size)
            else:  # We count!
                count_data['background'] += 1
        else:  # The ROI is a target
            if not count:
                number = target_dict[roi.name]
                prob = probability_dict[roi.name]
                if random() <= prob:
                    add_points_to_sample(roi, data_set, number, neigborhood_size)
            else:
                count_data[roi.name] += 1
    if count:
        return count_data
    else:
        return data_set


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
