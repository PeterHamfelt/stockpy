import numpy as np
import pandas as pd
from torch.utils.data import DataLoader
from typing import Union, Tuple, List
import torch
from ._dataset import StockDatasetRNN
from ._dataset import StockDatasetFFNN
from ._dataset import StockDatasetCNN
from ._data import ZScoreNormalizer
from ._data import MinMaxNormalizer
from ._data import RobustScaler
from ..config import Config as cfg

class StockScaler:
    
    def __init__(self): 
        self.scaler_type = cfg.training.scaler_type
        scaler_classes = {
            'zscore': ZScoreNormalizer,
            'minmax': MinMaxNormalizer,
            'robust': RobustScaler,
        }

        if self.scaler_type not in scaler_classes:
            raise ValueError(f'Invalid scaler type: {self.scaler_type}')
        
        self.X_normalizer = scaler_classes[self.scaler_type]()
        self.y_normalizer = scaler_classes[self.scaler_type]()

    def fit_transform(self, 
                      X_train: Union[np.ndarray, pd.core.frame.DataFrame],
                      y_train: Union[np.ndarray, pd.core.frame.DataFrame] = None,
                      task: str = None):
        
        X_train = torch.tensor(X_train.values).float()
        self.X_normalizer.fit(X_train)
        X_train = self.X_normalizer.transform(X_train)

        if y_train is not None and task == 'regression':
            y_train = torch.tensor(y_train.values).reshape(-1, 1 if len(y_train.shape) == 1 \
                                                            or y_train.shape[1] == 1 \
                                                            else y_train.shape[1]).float()
            self.y_normalizer.fit(y_train)
            y_train = self.y_normalizer.transform(y_train)

        elif task == 'classification':
            # If y_train contains label 0 don't subtract 1
            if y_train.min() == 0:
                y_train = torch.tensor(y_train.values).squeeze().long()
            else:
                y_train = torch.tensor(y_train.values).squeeze().long() - 1

        else:
            y_train = None
        
        return X_train, y_train

    def transform(self, 
                  X_test: torch.Tensor):
        
        X_test = self.X_normalizer.transform(X_test)
        
        return X_test
    
    def inverse_transform(self,
                          y_pred: torch.Tensor):

        return self.y_normalizer.inverse_transform(y_pred)

class StockDataloader:
    def __init__(self,
                 X: Union[np.ndarray, pd.core.frame.DataFrame],
                 y: Union[np.ndarray, pd.core.frame.DataFrame] = None,
                 model_type: str = None,
                 task: str = None
                 ):
        
        self.scaler = StockScaler()
        self.task = task
        
        self.X_train, self.y_train = self.scaler.fit_transform(X, y, task)
        self.model_type = model_type

        self.datasets = {
            'rnn': StockDatasetRNN,
            'ffnn': StockDatasetFFNN,
            'cnn': StockDatasetCNN
        }

        self.dataset = self.datasets[self.model_type](self.X_train, self.y_train, self.task)

    def get_loader(self, 
                X: Union[np.ndarray, pd.core.frame.DataFrame] = None, 
                y: Union[np.ndarray, pd.core.frame.DataFrame] = None,
                mode: str = 'train'):
        
        if mode == 'train':
            start_idx = 0
            end_idx = int(0.8 * len(self.dataset))
            subset = torch.utils.data.Subset(self.dataset, range(start_idx, end_idx))
        
        elif mode == 'val':
            start_idx = int(0.8 * len(self.dataset))
            end_idx = len(self.dataset)
            subset = torch.utils.data.Subset(self.dataset, range(start_idx, end_idx))
        elif mode == 'test':
            X = torch.tensor(X.values).float()
            X_test = self.scaler.transform(X)
            if self.task == 'regression':
                subset = self.datasets[self.model_type](X=X_test, 
                                                        y=None, 
                                                        task=self.task)
            elif self.task == 'classification':
                # Ensure y is a tensor of longs, representing class labels
                y = torch.tensor(y.values).squeeze().long() - 1
                subset = self.datasets[self.model_type](X=X_test, 
                                                        y=y, 
                                                        task=self.task)
        else:
            raise ValueError("Invalid mode. Accepted modes: 'train', 'val' or 'test'")
        
        return DataLoader(subset, 
                        batch_size=cfg.training.batch_size,
                        shuffle=cfg.training.shuffle
                        )

    def inverse_transform_output(self, y_pred):
        return self.scaler.inverse_transform(y_pred)
