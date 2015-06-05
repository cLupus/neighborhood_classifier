# -*- coding: utf-8 -*-
"""
Contains the global variables
"""
__author__ = 'Sindre Nistad'


# norm_points_table = False
# extended_point_table = False

def init(norm_points=False, extended_point=False):
    """
    Initializes the global variables norm_points_table, and extended_point_table, which indicated if the respective
    tables are defined.
    :param extended_point:
    :param norm_points:
    """
    global norm_points_table
    global extended_point_table
    norm_points_table = norm_points
    extended_point_table = extended_point


def set_norm_points_table(val):
    """
    Sets the value of norm_points_table to True, or False
    :param val: The value that we want to set to the global variable norm_points_table
    :type val:  bool
    :return:    None
    """
    assert isinstance(val, bool)
    global norm_points_table
    norm_points_table = val


def set_extended_point_table(val):
    """
    Sets the value of extended_point_table to True, or False
    :param val: The value that we want to set to the global variable norm_points_table
    :type val:  bool
    :return:    None
    """
    assert isinstance(val, bool)
    global extended_point_table
    extended_point_table = val


def get_norm_points():
    """
    Getter for norm_points_table
    :return:    The current value of norm_points_table
    :rtype:     bool
    """
    global norm_points_table
    return norm_points_table


def get_extended_point():
    """
    Getter for extended_point_table
    :return:    The current value of extended_point_table
    :rtype:     bool
    """
    global extended_point_table
    return extended_point_table
