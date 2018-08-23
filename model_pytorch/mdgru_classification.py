__author__ = "Simon Andermatt"
__copyright__ = "Copyright (C) 2017 Simon Andermatt"

import numpy as np

from helper import argget, compile_arguments
from model_pytorch.mdrnn import MDGRUBlock
from model_pytorch.mdrnn.mdgru import MDRNN
from helper import collect_parameters, define_arguments
from . import ClassificationModel
import torch as th
from model_pytorch import init_weights
import torch.nn.functional as F


class MDGRUClassification(ClassificationModel):
    """ Provides a full MDGRU default network.

    Using this class,
    Using the parameters fc_channels and mdgru_channels, which have to be lists of the same length, a
    MDGRU network of a number of mdgru and voxel-wise fully connected layers can be generated. Strides can be
    set for each MDGRU layer as a list of lists of strides per dimension. Furthermore, entries in fc_channels may be
    None, when MDGRU layer should be stacked directly after each other.

    :param fc_channels: Defines the number of channels per voxel-wise fully connected layer
    :param mdgru_channels: Defines the number of channels per MDGRU layer
    :param strides: list of list defining the strides per dimension per MDGRU layer. None means strides of 1
    :param data_shape: subvolume size
    """
    def __init__(self, data_shape, dropout, kw):
        super(MDGRUClassification, self).__init__(data_shape, dropout, kw)
        my_kw, kw = compile_arguments(MDGRUClassification, kw, transitive=False)
        for k, v in my_kw.items():
            setattr(self, k, v)
        self.fc_channels = argget(kw, "fc_channels", [25, 45, self.nclasses])
        self.mdgru_channels = argget(kw, "mdgru_channels", [16, 32, 64])
        self.strides = argget(kw, "strides", [None for _ in self.mdgru_channels])
        self.data_shape = data_shape
        #create logits:
        logits = []
        num_spatial_dims = len(data_shape[2:])
        last_output_channel_size = data_shape[1]
        for it, (mdgru, fcc, s) in enumerate(zip(self.mdgru_channels, self.fc_channels, self.strides)):
            mdgru_kw = {}
            mdgru_kw.update(kw)
            if it == len(self.mdgru_channels) - 1:
                mdgru_kw["noactivation"] = True
            if s is not None:
                mdgru_kw["strides"] = [s for _ in range(num_spatial_dims)] if np.isscalar(s) else s
            logits += [MDGRUBlock(num_spatial_dims, self.dropout, last_output_channel_size, mdgru, fcc, mdgru_kw)]
            last_output_channel_size = fcc if fcc is not None else mdgru
        self.model = th.nn.Sequential(*logits)
        self.loss = th.nn.modules.CrossEntropyLoss()
        print(self.model)

    def prediction(self, batch):
        """Provides prediction in the form of a discrete probability distribution per voxel"""
        pred = F.softmax(self.model(batch))
        return pred

    def initialize(self):
        self.model.apply(init_weights)

    @staticmethod
    def collect_parameters():
        args = collect_parameters(MDGRUBlock, {})
        args = collect_parameters(MDRNN, args)
        args = collect_parameters(MDRNN._defaults['crnn_class']['value'], args)
        return args

    @staticmethod
    def compile_arguments(kw, keep_entries=True):
        block_kw, kw = compile_arguments(MDGRUBlock, kw, transitive=True, keep_entries=keep_entries)
        mdrnn_kw, kw = compile_arguments(MDRNN, kw, transitive=True, keep_entries=keep_entries)
        crnn_kw, kw = compile_arguments(MDRNN._defaults['crnn_class']['value'], kw, transitive=True, keep_entries=keep_entries)
        new_kw = {}
        new_kw.update(crnn_kw)
        new_kw.update(mdrnn_kw)
        new_kw.update(block_kw)
        return new_kw, kw


class MDGRUClassificationCC(MDGRUClassification):

    # _defaults = {'use_connected_component_dice_loss': {'value': False, 'help': 'Use connected component dice loss, needs connected component labelling in griddatacollection to be performed. experimental', 'type': int}}

    def __init__(self, data_shape, dropout, kw):
        super(MDGRUClassificationCC, self).__init__(data_shape, dropout, kw)
        # self.dice_loss_label = argget(kw, "dice_loss_label", [])
        self.dice_loss_weight = argget(kw, "dice_loss_weight", []) #here, this should contain one value!
        my_kw, kw = compile_arguments(MDGRUClassificationCC, kw, transitive=False)
        for k, v in my_kw.items():
            setattr(self, k, v)
        self.ce = th.nn.modules.CrossEntropyLoss()

    def loss(self, prediction, labels):
        tp = 0
        nlabs = labels.max().cpu().item()
        for i in range(1, labels.max().cpu().data[0]):
            mask = labels == i
            tp += th.sum(prediction[:, 1] * mask)/th.sum(mask)
        fp = th.sum(prediction[:, 0] * (labels == 0))/th.sum(labels == 0)
        diceLoss = 2*tp/(tp+nlabs+fp)
        return np.sum(self.dice_loss_weight) * diceLoss + (1-np.sum(self.dice_loss_weight)) * self.ce(prediction, labels > 0)
