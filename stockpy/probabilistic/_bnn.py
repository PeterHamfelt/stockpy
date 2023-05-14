from abc import abstractmethod, ABCMeta
import os
import torch
import torch.nn as nn

import pyro
import pyro.distributions as dist
from pyro.nn import PyroModule, PyroSample
from pyro.infer.autoguide import AutoNormal
from pyro.infer import (
    SVI,
    Trace_ELBO,
    Predictive,
    TraceMeanField_ELBO
)
from typing import Union, Tuple
import pandas as pd
import numpy as np
from ._base import ClassifierProb
from ._base import RegressorProb
from ..config import Config as cfg

class BayesianNNClassifier(ClassifierProb):

    model_type = "ffnn"
   
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _init_model(self):
        # Check if hidden_sizes is a single integer and, if so, convert it to a list
        if isinstance(cfg.prob.hidden_size, int):
            self.hidden_sizes = [cfg.prob.hidden_size]
        else:
            self.hidden_sizes = cfg.prob.hidden_size

        layers = []
        input_size = self.input_size
        for hidden_size in self.hidden_sizes:
            layer = PyroModule[nn.Linear](input_size, hidden_size)
            layers.append(layer)
            layers.append(PyroModule[nn.ReLU]())
            layers.append(PyroModule[nn.Dropout](cfg.comm.dropout))
            input_size = hidden_size

        output_layer = PyroModule[nn.Linear](input_size, self.output_size)
        layers.append(output_layer)

        self.layers = PyroModule[nn.Sequential](*layers)

    def forward(self, x_data: torch.Tensor, 
                y_data: torch.Tensor=None) -> torch.Tensor:
        """
        Computes the forward pass of the Bayesian Neural Network model using Pyro.

        :param x_data: the input data tensor
        :type x_data: torch.Tensor
        :param y_data: the target data tensor
        :type y_data: torch.Tensor

        :returns: the output tensor of the model
        :rtype: torch.Tensor
        """
        if self.layers is None:
            raise Exception("Model has not been initialized.")
        
        x = self.layers(x_data)
        
        # apply softmax to the output to get class probabilities
        x = nn.functional.softmax(x, dim=1)

        with pyro.plate("data", x_data.shape[0]):
            obs = pyro.sample("obs", dist.Categorical(probs=x).to_event(1), obs=y_data)
            
        return x
    
    def _initSVI(self) -> pyro.infer.svi.SVI:
        self.guide = AutoNormal(self.forward)
        return SVI(model=self.forward,
                   guide=self.guide,
                   optim=self.optimizer, 
                   loss=TraceMeanField_ELBO())


class BayesianNNRegressor(RegressorProb):

    model_type = "ffnn"
   
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _init_model(self):
        # Check if hidden_sizes is a single integer and, if so, convert it to a list
        if isinstance(cfg.prob.hidden_size, int):
            self.hidden_sizes = [cfg.prob.hidden_size]
        else:
            self.hidden_sizes = cfg.prob.hidden_size

        layers = []
        input_size = self.input_size
        for hidden_size in self.hidden_sizes:
            layer = PyroModule[nn.Linear](input_size, hidden_size)
            layers.append(layer)
            layers.append(PyroModule[nn.ReLU]())
            layers.append(PyroModule[nn.Dropout](cfg.comm.dropout))
            input_size = hidden_size

        output_layer = PyroModule[nn.Linear](input_size, self.output_size)
        layers.append(output_layer)

        self.layers = PyroModule[nn.Sequential](*layers)

    def forward(self, x_data: torch.Tensor, 
                y_data: torch.Tensor=None) -> torch.Tensor:
        """
        Computes the forward pass of the Bayesian Neural Network model using Pyro.

        :param x_data: the input data tensor
        :type x_data: torch.Tensor
        :param y_data: the target data tensor
        :type y_data: torch.Tensor

        :returns: the output tensor of the model
        :rtype: torch.Tensor
        """
        x =  self.layers(x_data)
        # use StudentT distribution instead of Normal
        df = pyro.sample("df", dist.Exponential(1.))
        scale = pyro.sample("scale", dist.HalfCauchy(2.5))
        with pyro.plate("data", x_data.shape[0]):
            obs = pyro.sample("obs", dist.StudentT(df, x, scale).to_event(1), 
                              obs=y_data)
            
        return x
    
    def _initSVI(self) -> pyro.infer.svi.SVI:
        self.guide = AutoNormal(self.forward)
        return SVI(model=self.forward,
                   guide=self.guide,
                   optim=self.optimizer, 
                   loss=TraceMeanField_ELBO())
    
    def _predict(self,
                test_dl : torch.utils.data.DataLoader
                ) -> torch.Tensor:

        return self._predictNN(test_dl)
    

    