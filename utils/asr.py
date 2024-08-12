"""
"""

from pydub import AudioSegment
import numpy as np
import os
from scipy.signal import resample
import re
from tqdm.auto import tqdm


def read_mp3(path):
    """
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


## sample minutes of audio
def sample_audio(
    audio_dict, start_from=None, minutes=None
):
    audio = audio_dict['array']
    sampling_rate = audio_dict['sampling_rate']
    
    start_from = int(start_from*60*sampling_rate) if start_from else 0
    up_to = start_from + int(minutes*60*sampling_rate) if minutes else None
        
    return audio[start_from:up_to]

## Change sampling_rate
def update_sampling_rate(audio_data, original_rate, target_rate):
    num_samples = round(len(audio_data) * float(target_rate) / original_rate)
    resampled_audio = resample(audio_data, num_samples)
    return resampled_audio

## Transcripe audio
def transcripe_audio(
    audio,
    processor,
    model,
    sampling_rate=16_000,
    skip_special_tokens=True,
):
    input_features = processor(
        audio, sampling_rate=sampling_rate, return_tensors="pt"
    ).input_features

    predicted_ids = model.generate(input_features)

    return processor.batch_decode(
        predicted_ids, skip_special_tokens=skip_special_tokens
    )


def merge_transcripts(transcripts):
    """
    Merges a list of transcripts into a coherent and grammatically correct speech.

    Args:
        transcripts (list of str): List of transcribed text chunks.

    Returns:
        str: Merged and coherent speech.
    """
    merged_transcript = ""
    
    for i, transcript in enumerate(transcripts):
        # Strip leading/trailing whitespace from the transcript
        transcript = transcript.strip()
        
        # If it's not the first chunk, try to merge smoothly with the previous one
        if i > 0:
            # Handle cases where the previous chunk ends in an incomplete sentence
            if re.match(r'^\w', transcript):
                # Append a space if the transcript starts with a word character (alphanumeric)
                merged_transcript += " " + transcript
            else:
                # Directly append if the transcript starts with punctuation
                merged_transcript += transcript
        else:
            merged_transcript += transcript
    
    # Final pass to fix any spacing issues
    merged_transcript = re.sub(r'\s+', ' ', merged_transcript).strip()
    
    return merged_transcript


## Transcripe full episode
def transcripe_episode(
    episode,
    processor,
    model,
    skip_special_tokens=True,
    **sampling_kwargs,
):
    minutes=sampling_kwargs.get('minutes', 2)
    target_sampling_rate=sampling_kwargs.get('target_sampling_rate', 16_000)
    
    transcripts_list = []
    episode_length = len(episode['array'])
    orig_sampling_rate = episode['sampling_rate']
    
    
    # Calculate the total duration of the episode in seconds
    episode_duration_seconds = episode_length / orig_sampling_rate
    
    # Calculate the list of start_from values in minutes (could be float)
    start_froms = [i * minutes for i in range(int(episode_duration_seconds // (minutes * 60)) + 1)]
    
    for start_from in tqdm(start_froms):
        if start_from*60 == episode_duration_seconds:
            break
        
        audio = sample_audio(
            episode, start_from=start_from ,minutes=minutes)      
        audio = update_sampling_rate(
            audio, orig_sampling_rate, target_sampling_rate)
        transcripts_list += transcripe_audio(
            audio, processor, model, target_sampling_rate, skip_special_tokens)
    
    return merge_transcripts(transcripts_list)


def get_resuming_index(data_dir):
    filenames = os.listdir(data_dir)
    
    if not filenames:
        return 0
    
    return max([
        int(filename.split('.')[0][2:]) for filename in filenames
    ]) + 1