import torch
import os
import csv

from scipy.io.wavfile import read
from torch.utils.data import Dataset as ParentDataset

import librosa as li
import numpy as np
import pandas as pd

from Parameters import AUDIO_PATH, RAW_PATH, RAW_DATA_FRECUENCY, SAMPLES_PER_FILE

# Possible modes : DEBUG, INFO, RUN
PRINT_LEVEL = "INFO"


class Dataset(ParentDataset):
    """ F0 and Loudness dataset."""

    def __init__(self):
        self.audio_files = os.listdir(AUDIO_PATH)
        self.raw_files = os.listdir(RAW_PATH)

    def __len__(self):
        len_audio = len(self.audio_files)
        len_raw = len(self.raw_files)

        if len_audio == len_raw:
            return len_audio * SAMPLES_PER_FILE
        else:
            raise Exception("Length of data set does not fit.")

    def __getitem__(self, idx):
        file_idx = int(idx / 30)
        fragment_idx = idx % 30

        raw_file = self.raw_files[file_idx]
        frecuency_full = raw_2_tensor(raw_file)
        frecuency = frecuency_full[int(fragment_idx * 60 * RAW_DATA_FRECUENCY / SAMPLES_PER_FILE):
                                   int((fragment_idx+1) * 60 * RAW_DATA_FRECUENCY / SAMPLES_PER_FILE)]

        audio_file = self.audio_files[file_idx]
        loudness_full = audio_2_loudness_tensor(audio_file)
        loudness = loudness_full[0, int(fragment_idx * 60 * RAW_DATA_FRECUENCY / SAMPLES_PER_FILE):
                                   int((fragment_idx + 1) * 60 * RAW_DATA_FRECUENCY / SAMPLES_PER_FILE)]

        sample = {'frecuency': frecuency, 'loudness': loudness}

        return sample


def raw_2_tensor(file_name):
    file_path = os.path.join(RAW_PATH, file_name)
    raw_data = pd.read_csv(file_path, header=0)
    raw_array = raw_data.to_numpy()
    frecuency_data = raw_array[:-1, 1]
    frecuency_tensor = torch.from_numpy(frecuency_data)

    return frecuency_tensor


def audio_2_loudness_tensor(file_name):
    file_path = os.path.join(AUDIO_PATH, file_name)
    [fs, data] = read(file_path)
    data = data.astype(np.float)
    frame_length = int(fs / RAW_DATA_FRECUENCY)
    loudness_array = li.feature.rms(data, hop_length=frame_length, frame_length=frame_length)
    loudness_tensor = torch.from_numpy(loudness_array)

    return loudness_tensor


def audio_2_loudness_tensor_old(file_name):
    if file_name[-4:-3] == ".":
        if file_name[-4:] == ".wav":
            file_path = os.path.join(AUDIO_PATH, file_name)
        else:
            print("This file is not a .wav")
    else:
        file_path = os.path.join(AUDIO_PATH, file_name + ".csv")

    if PRINT_LEVEL == "DEBUG" or PRINT_LEVEL == "INFO":
        print("Charging ", file_name, "...")

    try:
        [fs, data] = read(file_path)
        data = data.astype(np.float)

        nb_samples = len(data)
        frame_length = int(fs / RAW_DATA_FRECUENCY)
        nb_frames = int(nb_samples / frame_length)

        time = np.multiply(np.arange(nb_frames), 1 / RAW_DATA_FRECUENCY)
        loudness = li.feature.rms(data, hop_length=frame_length, frame_length=frame_length)[0, 0:nb_frames]

        time_loudness_data = np.stack([time, loudness], axis=0)

        loudness_tensor = torch.from_numpy(loudness)
        time_loudness_tensor = torch.from_numpy(time_loudness_data)

        if PRINT_LEVEL == "DEBUG":
            print("Audio charged.")

        return loudness_tensor  # time_loudness_tensor

    except UnboundLocalError:
        print("The file", file_name, "is not a .wav")
    except FileNotFoundError:
        print("There is no file", file_name, "in /Raw folder.")
