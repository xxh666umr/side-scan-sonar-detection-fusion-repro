#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auto-generated SWDD experiment: l_vit."""
import os

import torch.nn as nn

from yolox.exp import Exp as MyExp


class Exp(MyExp):
    def __init__(self):
        super(Exp, self).__init__()
        self.depth = 1.0
        self.width = 1.0
        self.input_size = (640, 640)
        self.test_size = (640, 640)
        self.random_size = (14, 26)
        self.exp_name = os.path.split(os.path.realpath(__file__))[1].split(".")[0]
        self.enable_mixup = False
        self.max_epoch = 300
        self.eval_interval = 10
        self.no_aug_epochs = 15

        # ViT / KD switches (fused pipeline)
        self.vit = True
        self.KD = False
        self.KD_online = False
        self.teacher = "yolox_l"
        self.teacher_weights = "weights/"
        self.folder_KD_directory = "KD-FPN-Images/"

        if self.KD and not self.KD_online:
            # offline KD disables online random augmentation for the student
            self.multiscale_range = 0
            self.mosaic_prob = 0
            self.mixup_prob = 0
            self.hsv_prob = 0
            self.flip_prob = 0.0
            self.degrees = 0.0
            self.translate = 0
            self.mosaic_scale = (1, 1)
            self.enable_mixup = False
            self.mixup_scale = (1, 1)
            self.shear = 0

        # dataset (override with -o data_dir/... if needed)
        self.data_dir = "datasets/COCO/SWDD/"
        self.train_ann = "instances_train2017.json"
        self.val_ann = "instances_val2017.json"
        self.test_ann = "instances_test2017.json"
        self.num_classes = 2

    def get_model(self, sublinear=False):
        def init_yolo(M):
            for m in M.modules():
                if isinstance(m, nn.BatchNorm2d):
                    m.eps = 1e-3
                    m.momentum = 0.03

        if "model" not in self.__dict__:
            from yolox.models import YOLOX, YOLOPAFPN, YOLOXHead
            in_channels = [256, 512, 1024]
            depthwise = False
            backbone = YOLOPAFPN(self.depth, self.width, in_channels=in_channels,
                                 depthwise=depthwise, vit=self.vit)
            head = YOLOXHead(self.num_classes, self.width, in_channels=in_channels, act=self.act,
                             depthwise=depthwise, KD=self.KD, KD_Online=self.KD_online,
                             folder_KD_directory=self.folder_KD_directory,
                             exp_name=self.exp_name, teacher=self.teacher,
                             teacher_weights=self.teacher_weights)
            self.model = YOLOX(backbone, head)
        self.model.apply(init_yolo)
        self.model.head.initialize_biases(1e-2)
        return self.model
