import numpy as np
import torch.nn as nn
import torch.nn.functional as func

from parameters import *


class MLP(nn.Module):
    def __init__(self, input_size, output_size):
        super(MLP, self).__init__()

        """ 1st step """
        self.dense1 = nn.Linear(input_size, output_size)
        self.norm1 = nn.LayerNorm(output_size)

        """ 2nd step """
        self.dense2 = nn.Linear(output_size, output_size)
        self.norm2 = nn.LayerNorm(output_size)

        """ 3rd step """
        self.dense3 = nn.Linear(output_size, output_size)
        self.norm3 = nn.LayerNorm(output_size)

    def forward(self, x):
        y = func.relu(self.norm1(self.dense1(x)))
        y = func.relu(self.norm2(self.dense2(y)))
        y = func.relu(self.norm3(self.dense3(y)))

        return y


class DDSPNet(nn.Module):
    def __init__(self):
        super(DDSPNet, self).__init__()

        self.mlp_f0 = MLP(1, LINEAR_OUT_DIM)
        self.mlp_lo = MLP(1, LINEAR_OUT_DIM)
        self.gru = nn.GRU(2*LINEAR_OUT_DIM, HIDDEN_DIM, batch_first=True)
        self.mlp = MLP(HIDDEN_DIM, HIDDEN_DIM)
        self.dense_additive = nn.Linear(HIDDEN_DIM, NUMBER_HARMONICS+1)
        self.celu_additive = nn.CELU()

        if NOISE_AMPLITUDE:
            self.dense_noise = nn.Linear(HIDDEN_DIM, NUMBER_NOISE_BANDS+1)
        else:
            self.dense_noise = nn.Linear(HIDDEN_DIM, NUMBER_NOISE_BANDS)

    def forward(self, x):
        x_f0 = x["f0"]
        x_lo = x["lo"]

        """ MLP's """
        y_f0 = self.mlp_f0(x_f0)
        y_lo = self.mlp_lo(x_lo)

        """ Concatenate part """
        y = torch.cat((y_f0, y_lo), dim=2)
        y = self.gru(y)[0]
        y = self.mlp(y)

        y_noise = self.dense_noise(y)
        y_additive = self.dense_additive(y)

        if FINAL_SIGMOID == "None":
            pass
        elif FINAL_SIGMOID == "Usual":
            y_additive = torch.sigmoid(y_additive)
            y_noise = torch.sigmoid(y_noise)
        elif FINAL_SIGMOID == "Scaled":
            y_additive = 2 * torch.sigmoid(y_additive)**np.log(10) + 10e-7
            y_noise = 2 * torch.sigmoid(y_noise)**np.log(10) + 10e-7
        elif FINAL_SIGMOID == "Mixed":
            y_additive = 2 * torch.sigmoid(y_additive) ** np.log(10) + 10e-7
            y_noise = torch.sigmoid(y_noise)
        else:
            raise AssertionError("Final sigmoid not understood.")

        return y_additive, y_noise
