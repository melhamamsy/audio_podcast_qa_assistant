"""
This module provides utilities for processing, resampling, and transcribing
audio files, with a focus on working with MP3 files. It includes functions to
read and resample audio, extract specific segments, transcribe them using a
speech-to-text model, and merge the transcribed text into coherent speech.

Dependencies:
    - re
    - numpy
    - pydub
    - scipy
    - tqdm
"""

import re

import numpy as np
from pydub import AudioSegment
from scipy.signal import resample
from tqdm.auto import tqdm


def read_mp3(path):
    """
    Reads an MP3 file and converts it into a numpy array.

    Args:
        path (str): The path to the MP3 file.

    Returns:
        tuple: A tuple containing:
            - numpy.ndarray: The audio samples (mono or stereo).
            - int: The sampling rate of the audio file.
    """
    # Load the audio file
    audio = AudioSegment.from_file(path)

    # Convert to raw data
    samples = np.array(audio.get_array_of_samples())

    # If the audio is stereo, reshape to 2D array (channels x samples)
    if audio.channels == 2:
        samples = samples.reshape((-1, 2))

    # Get the sample rate
    sampling_rate = audio.frame_rate

    return samples, sampling_rate


def sample_audio(audio_dict, start_from=None, minutes=None):
    """
    Extracts a segment from the audio based on the specified start time and
    duration.

    Args:
        audio_dict (dict): A dictionary containing:
            - "array" (numpy.ndarray): The audio samples.
            - "sampling_rate" (int): The sampling rate of the audio.
        start_from (float, optional): The start time in minutes from which to
                                      begin sampling. Defaults to None (start
                                      from the beginning).
        minutes (float, optional): The duration of the segment to extract in
                                   minutes. Defaults to None (extract till
                                   the end).

    Returns:
        numpy.ndarray: The extracted audio segment.
    """
    audio = audio_dict["array"]
    sampling_rate = audio_dict["sampling_rate"]

    start_from = int(start_from * 60 * sampling_rate) if start_from else 0
    up_to = start_from + int(minutes * 60 * sampling_rate) if minutes else None

    return audio[start_from:up_to]


def update_sampling_rate(audio_data, original_rate, target_rate):
    """
    Resamples the audio data to a target sampling rate.

    Args:
        audio_data (numpy.ndarray): The audio samples to be resampled.
        original_rate (int): The original sampling rate of the audio.
        target_rate (int): The desired sampling rate.

    Returns:
        numpy.ndarray: The resampled audio data.
    """
    num_samples = round(len(audio_data) * float(target_rate) / original_rate)
    resampled_audio = resample(audio_data, num_samples)
    return resampled_audio


def transcripe_audio(
    audio,
    processor,
    model,
    sampling_rate=16_000,
    skip_special_tokens=True,
):
    """
    Transcribes audio data using a pre-trained speech-to-text model.

    Args:
        audio (numpy.ndarray): The audio samples to be transcribed.
        processor (object): The processor object used to preprocess the audio
                            data.
        model (object): The pre-trained model used for transcription.
        sampling_rate (int, optional): The sampling rate to be used during
                                       transcription. Defaults to 16,000.
        skip_special_tokens (bool, optional): Whether to skip special tokens
                                              during decoding. Defaults to True.

    Returns:
        list of str: The transcribed text.
    """
    input_features = processor(
        audio, sampling_rate=sampling_rate, return_tensors="pt"
    ).input_features

    predicted_ids = model.generate(input_features)

    return processor.batch_decode(
        predicted_ids, skip_special_tokens=skip_special_tokens
    )


def merge_transcripts(transcripts):
    """
    Merges a list of transcripts into a coherent and grammatically correct
    speech.

    Args:
        transcripts (list of str): List of transcribed text chunks.

    Returns:
        str: Merged and coherent speech.
    """
    merged_transcript = ""

    for i, transcript in enumerate(transcripts):
        # Strip leading/trailing whitespace from the transcript
        transcript = transcript.strip()

        if i > 0:
            # Handle cases where the transcript starts with punctuation (comma or dot)
            if re.match(r"^[,.]", transcript):
                # Remove the ending punctuation from the previous chunk if needed
                if merged_transcript.endswith(".") or merged_transcript.endswith(","):
                    merged_transcript = merged_transcript[:-1]

                # Directly append the next transcript chunk
                merged_transcript += transcript
            else:
                # If the transcript starts with a word character or other punctuation,
                # append with a space
                merged_transcript += " " + transcript
        else:
            # For the first chunk, directly add the transcript
            merged_transcript += transcript

    # Final pass to fix any spacing issues
    merged_transcript = re.sub(r"\s+", " ", merged_transcript).strip()

    return merged_transcript


def transcripe_episode(
    episode,
    processor,
    model,
    skip_special_tokens=True,
    **sampling_kwargs,
):
    """
    Transcribes an entire audio episode by breaking it into smaller segments.

    Args:
        episode (dict): A dictionary containing:
            - "array" (numpy.ndarray): The audio samples.
            - "sampling_rate" (int): The sampling rate of the audio.
        processor (object): The processor object used to preprocess the audio
                            data.
        model (object): The pre-trained model used for transcription.
        skip_special_tokens (bool, optional): Whether to skip special tokens
                                              during decoding. Defaults to True.
        **sampling_kwargs: Additional keyword arguments:
            - "minutes" (float): The duration of each segment in minutes.
                                 Defaults to 2 minutes.
            - "target_sampling_rate" (int): The sampling rate to be used
                                            during transcription. Defaults to
                                            16,000.

    Returns:
        str: The fully transcribed and merged episode text.
    """
    minutes = sampling_kwargs.get("minutes", 2)
    target_sampling_rate = sampling_kwargs.get("target_sampling_rate", 16_000)

    transcripts_list = []
    episode_length = len(episode["array"])
    orig_sampling_rate = episode["sampling_rate"]

    # Calculate the total duration of the episode in seconds
    episode_duration_seconds = episode_length / orig_sampling_rate

    # Calculate the list of start_from values in minutes (could be float)
    start_froms = [
        i * minutes for i in range(int(episode_duration_seconds // (minutes * 60)) + 1)
    ]

    for start_from in tqdm(start_froms):
        if start_from * 60 == episode_duration_seconds:
            break

        audio = sample_audio(episode, start_from=start_from, minutes=minutes)
        audio = update_sampling_rate(audio, orig_sampling_rate, target_sampling_rate)
        transcripts_list += transcripe_audio(
            audio, processor, model, target_sampling_rate, skip_special_tokens
        )

    return merge_transcripts(transcripts_list)
