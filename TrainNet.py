import torch
import time

import scipy.io.wavfile as wav
import os
import numpy as np

from Net import DDSPNet
from DataLoader import Dataset
from Synthese import synthetize
from torch.utils.data import DataLoader
from torch import optim
from Parameters import STFT_SIZE, PATH_TO_MODEL, NUMBER_EPOCHS, FRAME_LENGTH, AUDIO_SAMPLE_RATE, \
    DEVICE, SHUFFLE_DATALOADER, BATCH_SIZE, LEARNING_RATE, PATH_TO_CHECKPOINT


#### Debug settings ####
PRINT_LEVEL = "RUN"  # Possible modes : DEBUG, INFO, RUN, TRAIN

#### Pytorch settings ####
torch.set_default_tensor_type(torch.FloatTensor)

#### Net ####
net = DDSPNet().float()
net = net.to(DEVICE)
optimizer = optim.Adam(net.parameters(), lr=LEARNING_RATE)
loss_function = torch.nn.MSELoss()

if PRINT_LEVEL == "DEBUG" or PRINT_LEVEL == "INFO":
    print("Working device :", DEVICE)

#### Data ####
dataset = Dataset()
data_loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=SHUFFLE_DATALOADER)

#### Train ####

# Time #
if PRINT_LEVEL == "DEBUG" or PRINT_LEVEL == "INFO" or PRINT_LEVEL == "RUN" or PRINT_LEVEL == "TRAIN":
    time_start = time.time()
else:
    time_start = None
########

for epoch in range(NUMBER_EPOCHS):
    if PRINT_LEVEL == "DEBUG" or PRINT_LEVEL == "INFO" or PRINT_LEVEL == "RUN" or PRINT_LEVEL == "TRAIN":
        print("#### Epoch", epoch+1, "####")

    # Time #
    if PRINT_LEVEL == "DEBUG" or PRINT_LEVEL == "INFO" or PRINT_LEVEL == "RUN":
        time_epoch_start = time.time()
    else:
        time_epoch_start = None
    ########

    for i, data in enumerate(data_loader, 0):
        if PRINT_LEVEL == "DEBUG" or PRINT_LEVEL == "INFO" or PRINT_LEVEL == "RUN":
            print("## Data", i + 1, "##")

        # Time #
        if PRINT_LEVEL == "DEBUG" or PRINT_LEVEL == "INFO":
            time_data_start = time.time()
        else:
            time_data_start = None
        ########

        fragments, waveforms = data

        # Time #
        if PRINT_LEVEL == "DEBUG":
            time_device_start = time.time()

        fragments["f0"] = fragments["f0"].to(DEVICE)
        fragments["lo"] = fragments["lo"].to(DEVICE)

        # Time #
        if PRINT_LEVEL == "DEBUG":
            time_device_end = time.time()
            print("Time to device :", round(time_device_end - time_device_start, 5), "s")
        ########

        optimizer.zero_grad()

        # Time #
        if PRINT_LEVEL == "DEBUG":
            time_pre_net = time.time()
        else:
            time_pre_net = None
        ########

        y = net(fragments)

        # Time #
        if PRINT_LEVEL == "DEBUG":
            time_post_net = time.time()
            print("Time through net :", round(time_post_net - time_pre_net, 3), "s")
        ########

        f0s = fragments["f0"][:, :, 0]
        a0s = y[:, :, 0]
        aa = y[:, :, 1:]

        # Time #
        if PRINT_LEVEL == "DEBUG":
            time_pre_synth = time.time()
        else:
            time_pre_synth = None
        ########

        sons = synthetize(a0s, f0s, aa, FRAME_LENGTH, AUDIO_SAMPLE_RATE)

        # for k in range(sons.shape[0]):
        #     son_synth = sons[k, :]
        #     son_original = waveforms[k][0:son_synth.shape[0]]
        #     wav.write(os.path.join("Outputs", str(i) + "_synth.wav"), AUDIO_SAMPLE_RATE, son_synth.detach().numpy().astype(np.float32))
        #     wav.write(os.path.join("Outputs", str(i) + "_original.wav"), AUDIO_SAMPLE_RATE, son_original.detach().numpy())


        # Time #
        if PRINT_LEVEL == "DEBUG":
            time_post_synth = time.time()
            print("Time to synthetize :", round(time_post_synth - time_pre_synth, 3), "s")
        else:
            time_post_synth = None
        ########

        """ STFT's """
        waveforms = waveforms.to(DEVICE)
        window = torch.hann_window(STFT_SIZE, device=DEVICE)

        stfts = torch.stft(sons, STFT_SIZE, window=window, onesided=True)
        squared_modules = stfts[:, :, :, 0] ** 2 + stfts[:, :, :, 1] ** 2
        stft_originals = torch.stft(waveforms[:, 0:sons.shape[1]], STFT_SIZE, window=window, onesided=True)
        squared_module_originals = stft_originals[:, :, :, 0] ** 2 + stft_originals[:, :, :, 1] ** 2

        # Time #
        if PRINT_LEVEL == "DEBUG":
            time_post_stft = time.time()
            print("Time to perform stfts :", round(time_post_stft - time_post_synth, 3), "s")
        else:
            time_post_stft = None
        ########

        loss = loss_function(squared_modules, squared_module_originals) \
               + loss_function(torch.log(squared_modules + 1e-20), torch.log(squared_module_originals + 1e-20))
        loss.backward()
        optimizer.step()

        # Time #
        if PRINT_LEVEL == "DEBUG" or PRINT_LEVEL == "INFO":
            time_data_end = time.time()
        else:
            time_data_end = None
        if PRINT_LEVEL == "DEBUG":
            print("Time to backpropagate :", round(time_data_end - time_post_stft, 3), "s")

        ########

        if PRINT_LEVEL == "DEBUG" or PRINT_LEVEL == "INFO" or PRINT_LEVEL == "RUN":
            print("Loss :", loss.item())

        # Time #
        if PRINT_LEVEL == "DEBUG" or PRINT_LEVEL == "INFO":
            print("Total time :", round(time_data_end - time_data_start, 3), "s")
        ########

    # Time #
    if PRINT_LEVEL == "DEBUG" or PRINT_LEVEL == "INFO" or PRINT_LEVEL == "RUN":
        time_epoch_end = time.time()
        print("Time of the epoch :", round(time_epoch_end - time_epoch_start, 3), "s\n\n\n------------\n\n\n")
    ########

    torch.save(net.state_dict(), PATH_TO_CHECKPOINT)

#### Save ####
torch.save(net.state_dict(), PATH_TO_MODEL)

# Time #
if PRINT_LEVEL == "DEBUG" or PRINT_LEVEL == "INFO" or PRINT_LEVEL == "RUN" or PRINT_LEVEL == "TRAIN":
    time_end = time.time()
    print("Time of training :", round((time_end - time_start) // 60), "m", round((time_end - time_start) % 60, 3), "s")
########

#### Synth ####
for k in range(sons.shape[0]):
    son_synth = sons[k, :]
    son_original = waveforms[k][0:son_synth.shape[0]]
    wav.write(os.path.join("Outputs", str(k) + "_synth.wav"), AUDIO_SAMPLE_RATE,
              son_synth.cpu().detach().numpy().astype(np.float32))
    wav.write(os.path.join("Outputs", str(k) + "_original.wav"), AUDIO_SAMPLE_RATE, son_original.cpu().detach().numpy())
