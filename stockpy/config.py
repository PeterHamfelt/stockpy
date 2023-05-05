import torch
from dataclasses import dataclass

@dataclass
class Common:
    input_size: int = 4
    hidden_size: int = 32
    output_size: int = 10
    num_filters: int = 32
    pool_size: int = 1
    kernel_size: int = 3

@dataclass
class NN(Common):
    num_layers: int = 2

@dataclass
class Prob(Common):
    rnn_dim: int = 32
    z_dim: int = 32
    emission_dim: int = 32
    transition_dim: int = 32
    variance: float = 0.1

@dataclass
class Shared:
    dropout: float = 0.2
    pretrained: bool = False
    lr: float = 0.001
    betas: tuple = (0.9, 0.999)
    lrd: float = 0.99996
    clip_norm: float = 10.0
    weight_decay: float = 0.001
    eps: float = 1e-8
    amsgrad: bool = False
    optim_args: float = 0.01
    gamma: float = 0.1
    step_size: float = 50

@dataclass
class Training:
    epochs: int = 10
    batch_size: int = 24
    sequence_length: int = 30
    use_cuda = torch.cuda.is_available()
    device: str = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    num_workers: int = 4
    validation_cadence: int = 5
    patience: int = 5
    prediction_window: int = 1

@dataclass
class Config:
    comm: Common = Common()
    nn: NN = NN()
    prob: Prob = Prob()
    shared: Shared = Shared()
    training: Training = Training()

