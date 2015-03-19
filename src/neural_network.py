__author__ = 'Sindre Nistad'

from warnings import warn
from pybrain.datasets import ClassificationDataSet
from pybrain.tools.shortcuts import buildNetwork
from pybrain.structure.modules import SoftmaxLayer
from regions_of_interest import RegionsOfInterest


class ClassificationNet():

    def __init__(self, rois, targets, target_background=True, neigborhood_size=1):
        """
            Initializes a neural network for classification.
        :param rois:                A RegionsOfInterest object containing the ROIs
        :param target_background:   Toggles mode: if true, then we are only interested in classifying ONE target, and
                                    then consider all the other targets as background. If false, the net will try to
                                    classify every target.
        :param targets:             A list of strings with the target(s)
        :param neigborhood_size:    The size (diameter in pixels) of the neigborhood the neural network considers.

        :type rois: RegionsOfInterest
        :type target_background: bool
        :type targets: list[str]
        :type neigborhood_size: int
        :return:
        """
        if neigborhood_size % 2 == 0:
            warn("The size of the neigborhood should be an odd number! Continuing")
        self.target_background = target_background
        self.num_targets = targets
        self.neigborhood_size = neigborhood_size
        self.net = None
        self.dataset = load_dataset(rois, targets, neigborhood_size, target_background)

    def train_network(self):
        pass

    def set_target(self, target):
        pass

    def save(self, path):
        pass


def build_net(indim, hiddendim, outdim):
    return buildNetwork(indim, hiddendim, outdim, outclass=SoftmaxLayer)
    pass


def load_dataset(roi_obj, targets, neigborhood_size, have_background=True):
    """
        A method that loads the data set from a RegionsOfInterest object, to a ClassificationDataSet.
        Only the relevant targets needs to be specified, as background will be added automatically.
    :param roi_obj:             The ROI object
    :param targets:             The list of targets (may contain only one + background)
    :param neigborhood_size:    The diameter of the neigborhood

    :type roi_obj: RegionsOfInterest
    :type targets: list[str]
    :type neigborhood_size: int
    :return: A data set sorting all the
    :rtype: ClassificationDataSet
    """
    num_bands = len(roi_obj[targets[0]].points[0].bands)
    if have_background:
        targets.append('background')
    data_set = ClassificationDataSet(neigborhood_size ** 2 * num_bands,
                                     nb_classes=len(targets),
                                     class_labels=targets)
    for roi in roi_obj.rois:
        if roi.name == 'background' or roi.name not in targets:
            # TODO: consider it as background
            for point in roi.points:
                data_set.addSample(point.bands, 'background')
        else:  # The ROI is a target
            for point in roi.points:
                data_set.addSample(point.bands, roi.name)
    return data_set

