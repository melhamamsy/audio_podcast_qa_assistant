"""
This module provides utility functions for processing episodes to extract
questions and group them by episode. The main functionalities include:
    1. Extracting questions from episode segments based on specific criteria.
    2. Grouping extracted questions by episode for further processing or analysis.
"""

from collections import defaultdict


def extract_questions(
    episode,
    min_words=11,
):
    """
    Extract questions from episode segments based on specific criteria.

    Args:
        episode (dict): The episode data containing segments of text.
        min_words (int, optional): The minimum number of words required for a
                                   segment to be considered a question. Defaults to 11.

    Returns:
        list of dict: A list of extracted questions with episode IDs.
    """
    questions = []
    epidose_id = episode["id"]

    for segment in episode["segments"]:
        if "?" == segment["text"][-1]:
            segment_text_list = segment["text"].split()
            if segment_text_list[0].istitle():
                if len(segment_text_list) >= min_words:
                    questions.append(
                        {"episode_id": epidose_id, "question": segment["text"]}
                    )

    return questions


def group_questions_by_episode(questions):
    """
    Group extracted questions by episode.

    Args:
        questions (list of dict): A list of questions with episode IDs.

    Returns:
        list of list of dict: A list where each element contains the questions
                              for a specific episode.
    """
    questions_per_episode = defaultdict(list)
    for question in questions:
        questions_per_episode[question["episode_id"]].append(question)

    questions_per_episode = list(questions_per_episode.values())
    return questions_per_episode
