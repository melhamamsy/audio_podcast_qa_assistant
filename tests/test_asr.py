"""
Unit tests for utils.asr module.
"""

# import pdb; # pdb.set_trace();
from pathlib import Path

import numpy as np

# from utils.asr import read_mp3
from utils.asr import merge_transcripts, sample_audio, update_sampling_rate

PROJECT_DIR = Path(__file__).resolve().parent.parent


# def test_read_mp3():
#     """
#     test read_mp3 function
#     """

#     expected_seconds_351 = 2*60*60 + 24*60 + 50
#     expected_seconds_367 = 2*60*60 + 28*60 + 9

#     samples, sampling_rate = read_mp3(os.path.join(
#         PROJECT_DIR,
#         "bucket/351/episode.mp3"
#     ))
#     actual_seconds_351 = samples.shape[0] / sampling_rate

#     samples, sampling_rate = read_mp3(os.path.join(
#         PROJECT_DIR,
#         "bucket/367/episode.mp3"
#     ))
#     actual_seconds_367 = samples.shape[0] / sampling_rate

#     assert abs(expected_seconds_351 - actual_seconds_351) < 1, "351"
#     assert abs(expected_seconds_367 - actual_seconds_367) < 1, "367"


def test_sample_audio():
    """
    test sample_audio function
    """
    # Create a dummy audio array of 10 minutes (10 * 60 seconds)
    sampling_rate = 48000  # kHz
    # 10 minutes in seconds
    total_duration = 10 * 60
    # Simulating a simple random array
    audio_array = np.random.random(size=total_duration * sampling_rate)

    audio_dict = {"array": audio_array, "sampling_rate": sampling_rate}

    # Test 1: Extract first 2 minutes of audio
    result = sample_audio(audio_dict, start_from=0, minutes=2)
    expected_length = 2 * 60 * sampling_rate
    assert len(result) == expected_length
    assert np.array_equal(result, audio_array[:expected_length])

    # Test 2: Extract 1 minute from the 5th minute
    result = sample_audio(audio_dict, start_from=5, minutes=1)
    start_index = 5 * 60 * sampling_rate
    expected_length = 1 * 60 * sampling_rate
    assert len(result) == expected_length
    assert np.array_equal(
        result, audio_array[start_index : start_index + expected_length]
    )

    # Test 3: Extract till the end starting from the 8th minute
    result = sample_audio(audio_dict, start_from=8)
    start_index = 8 * 60 * sampling_rate
    assert len(result) == len(audio_array) - start_index
    assert np.array_equal(result, audio_array[start_index:])

    # Test 4: Extract from the beginning without specifying duration
    result = sample_audio(audio_dict)
    assert len(result) == len(audio_array)
    assert np.array_equal(result, audio_array)

    # Test 5: Test with invalid input (start_from beyond the audio duration)
    result = sample_audio(
        audio_dict, start_from=15
    )  # Beyond the total duration (10 minutes)
    assert len(result) == 0  # Expecting an empty result


def test_update_sampling_rate():
    """
    test update_sampling_rate function
    """
    # Create a dummy audio array with a known pattern
    original_rate = 48000  # Original sampling rate: 48 kHz
    target_rate = 16000  # Target sampling rate: 16 kHz

    duration = 1  # 1 second of audio
    original_audio = np.sin(
        2 * np.pi * np.arange(original_rate * duration) * 440 / original_rate
    )  # 440 Hz sine wave

    # Call the update_sampling_rate function
    resampled_audio = update_sampling_rate(original_audio, original_rate, target_rate)

    # Expected number of samples after resampling
    expected_num_samples = int(round(len(original_audio) * target_rate / original_rate))

    # Check if the resampled audio has the expected number of samples
    assert len(resampled_audio) == expected_num_samples

    # Check if the resampled audio is still a valid array (no NaN values, no infinities)
    assert np.isfinite(resampled_audio).all()

    # Test if the resampling roughly maintains the original signal characteristics
    # This checks that the resampled audio still represents a sine wave, although downsampled
    resampled_audio_reconstructed = np.sin(
        2 * np.pi * np.arange(len(resampled_audio)) * 440 / target_rate
    )
    correlation = np.corrcoef(resampled_audio, resampled_audio_reconstructed)[0, 1]
    assert (
        correlation > 0.9
    )  # The correlation should be high if the resampling is reasonable


def test_merge_transcripts():
    """
    test merge_transcripts function
    """
    # Test 1: Merging simple transcript chunks with clean transitions
    transcripts = [
        "This is the first part.",
        "This is the second part.",
        "Finally, this is the third part.",
    ]
    result = merge_transcripts(transcripts)
    expected = "This is the first part. This is the second part. Finally, this is the third part."
    assert result == expected

    # Test 2: Handling leading and trailing whitespace in chunks
    transcripts = [
        "  This is the first part.  ",
        "  And this is the second part.  ",
        "Finally, this is the third part.  ",
    ]
    result = merge_transcripts(transcripts)
    expected = str(
        "This is the first part. "
        "And this is the second part. "
        "Finally, this is the third part."
    )
    assert result == expected

    # Test 3: Handling a chunk starting with punctuation
    transcripts = [
        "This is the first part.",
        " However, this is the second part.",
        " Lastly, this is the third part.",
    ]
    result = merge_transcripts(transcripts)
    expected = str(
        "This is the first part. "
        "However, this is the second part. "
        "Lastly, this is the third part."
    )
    assert result == expected

    # Test 4: Handling a chunk starting with punctuation directly
    transcripts = [
        "This is the first part.",
        ", and here is the second part.",
        ". Finally, this is the third part.",
    ]
    result = merge_transcripts(transcripts)
    expected = str(
        "This is the first part, "
        "and here is the second part. "
        "Finally, this is the third part."
    )
    assert result == expected

    # Test 5: Handling empty or whitespace-only transcripts
    transcripts = [
        "This is the first part.",
        "   ",  # Empty chunk with only spaces
        "And this is the third part.",
    ]
    result = merge_transcripts(transcripts)
    expected = "This is the first part. And this is the third part."
    assert result == expected

    # Test 6: Single transcript without merging needed
    transcripts = ["This is a standalone transcript."]
    result = merge_transcripts(transcripts)
    expected = "This is a standalone transcript."
    assert result == expected

    # Test 7: No transcripts provided (empty list)
    transcripts = []
    result = merge_transcripts(transcripts)
    expected = ""  # Expecting an empty string
    assert result == expected
