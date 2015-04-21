# -*- coding: utf-8 -*-
"""
    A Class for the neural networks used for classification of regions of interest.
"""
__author__ = 'Sindre Nistad'

from warnings import warn
from cPickle import dump, load, HIGHEST_PROTOCOL
from math import ceil

from pybrain.datasets import ClassificationDataSet
from pybrain.tools.shortcuts import buildNetwork
from pybrain.structure.modules import TanhLayer, SigmoidLayer, LinearLayer
from pybrain.structure import FeedForwardNetwork
from pybrain.supervised.trainers import BackpropTrainer
from pybrain.tools.xml import NetworkReader, NetworkWriter
from pybrain.utilities import percentError
from pybrain.optimization.populationbased.ga import GA

from RegionOfInterest.regions_of_interest import RegionsOfInterest
from Common.data_management import load_data_set_from_regions_of_interest as load_data
from Common.data_management import get_histogram


class ClassificationNet(object):
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
                 hidden_ratio=0.5,
                 split_proportion=-1,
                 set_trainer=False):
        """
            Initializes a neural network for classification.
        :param rois:                        A RegionsOfInterest object containing the ROIs
        :param targets:                     A list of strings with the target(s), or a simple string
                                            for a single target.
        :param neigborhood_size:            The size (diameter in pixels) of the neigborhood the
                                            neural network considers.
        :param target_background:           Toggles mode: if true, then we are only interested in classifying ONE
                                            target, and then consider all the other targets as background.
                                            If false, the net will try to classify every target.
        :param targets_background_ration:   A list of target to background ratios; how much background should there
                                            in relation to target pixels. The default is to disable it.
        :param hidden_layer:                The number of input layers to the network. The default is to have half
                                            as many as there is input nodes and output nodes.
        :param hidden_ratio:                The ratio of hidden layers to the sum of input and output layers.
        :param split_proportion:            Defines how large a proportion will be given to as training data, and
                                            test/validation data. The proportion says what proportion will be used
                                            as test data. The default is to not split the data.
        :param set_trainer:                 Toggles whether or not the trainer should be created immediately or not.
                                            The default is yes.
        :type rois:                         RegionsOfInterest
        :type targets:                      list of [str] | str
        :type target_background:            bool
        :type targets_background_ration:    list of [float]
        :type neigborhood_size:             int
        :type hidden_layer:                 int
        :type hidden_ratio:                 float
        :type split_proportion:             float
        :type set_trainer:                  bool
        :return:
        """
        if neigborhood_size % 2 == 0:
            warn("The size of the neigborhood should be an odd number! Continuing")
        if isinstance(targets, str):
            # Allows a single string to be passed as target.
            targets = [targets]

        self.target_background = target_background
        """ :type : bool """
        self.targets = targets
        """ :type : list of [str] """
        self.neigborhood_size = neigborhood_size
        """ :type : int """
        self.data_set = load_data(rois, targets, neigborhood_size,
                                  targets_background_ratios=targets_background_ration,
                                  have_background=target_background)
        input_layers = self.data_set.indim
        output_layer = self.data_set.outdim
        if hidden_layer < 0:
            hidden_layer = int(ceil((input_layers + output_layer) * hidden_ratio))

        """ :type : ClassificationDataSet """
        self.neural_net = build_net(input_layers, hidden_layer, output_layer)
        """ :type : FeedForwardNetwork """
        self.histogram = get_histogram(rois.get_all(), targets, count_points=True)
        """ :type: dict of [str, int] """
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
            self.trainer = BackpropTrainer(self.neural_net, self.data_set,
                                           learning_rate, lrdecay, momentum, verbose,
                                           batch_learning, weight_decay)

    def train_network(self,
                      max_epochs=-1,
                      verbose=False,
                      continue_epochs=10,
                      validation_proportion=0.25,
                      force_split=False,
                      use_local=False):
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
        :param use_local:               Toggles whether or not PyBrain is to train the network. If not, the training
                                        will be done by a self-developed method.
        :type max_epochs:               int
        :type verbose:                  bool
        :type continue_epochs:          int
        :type validation_proportion:    float
        :type force_split:              bool
        :type use_local:                bool
        :return:                        None
        """
        if use_local:
            self._train(max_epochs, verbose, continue_epochs, validation_proportion, force_split)
        else:
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
                    self.trainer.trainUntilConvergence(self.data_set, None, verbose, continue_epochs,
                                                       validation_proportion)
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
        spited_path = path.split('.')
        ending = spited_path[-1]
        sub_ending = spited_path[-2]
        if ending == 'pkl' or ending == 'pickle':
            with open(path, 'wb') as handle:
                dump(self, handle, HIGHEST_PROTOCOL)
        elif ending == 'xml' or ending == 'nn' or (ending == 'net' and sub_ending == 'neural'):
            NetworkWriter.writeToFile(self.neural_net, path)
        elif ending == 'data':
            if sub_ending == 'training':
                with open(path, 'wb') as handle:
                    dump(self.training_data, handle, HIGHEST_PROTOCOL)
            elif sub_ending == 'validation':
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
        spited_path = path.split('.')
        ending = spited_path[-1]
        sub_ending = spited_path[-2]
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

    def _train(self, max_epochs, verbose, continue_epochs, validation_proportion, force_split):
        ga = GA(self.data_set.evaluateModuleMSE, self.neural_net, minimize=True)
        for i in range(max_epochs):
            self.neural_net = ga.learn(0)[0]
            if verbose:
                print(percentError(self.trainer.testOnClassData(self.data_set), self.data_set['class']))
        pass

    def is_better(self, other, validation_data):
        """
            Checks if this neural network is better than the other on the given validation data set.
        :param other:           The other network that is compared against.
        :param validation_data:
        :return:                True if this has a strictly better (lower) error score than other.
                                False if the other has a better (lower) error score than this.
        :type other:            ClassificationNet
        :type validation_data:  ClassificationDataSet
        :rtype:                 bool
        """
        my_score = percentError(self.trainer.testOnClassData(dataset=validation_data), validation_data['class'])
        other_score = percentError(other.trainer.testOnClassData(dataset=validation_data), validation_data['class'])
        if my_score < other_score:
            return True
        else:
            return False


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
    input_layer = LinearLayer
    hidden_layer = SigmoidLayer
    out_layer = TanhLayer
    return buildNetwork(indim, hiddendim, outdim, hiddenclass=hidden_layer, outclass=out_layer)


def make_nets(targets):
    nets = {}
    for target in targets:
        nets[target] = ClassificationNet()


