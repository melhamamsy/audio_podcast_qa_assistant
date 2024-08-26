"""
This module provides utility functions for processing episodes to extract
questions and group them by episode. The main functionalities include:
    1. Extracting questions from episode segments based on specific criteria.
    2. Grouping extracted questions by episode for further processing or analysis.
    3. Rephrase questions using openai
"""

import re
from collections import defaultdict
from json import JSONDecodeError

from utils.query import build_prompt
from utils.utils import parse_json_response
from utils.variables import OPENAI_CLIENT


def extract_questions(
    episode: dict, min_words: int = 15, max_words: int = 25
) -> list[dict]:
    """
    Extracts questions from an episode's text based on specified word count criteria.

    Parameters:
    ----------
    episode : dict
        A dictionary containing:
            - 'id': The unique identifier for the episode.
            - 'chunk_id': The identifier for the chunk of text.
            - 'text': The textual content from which to extract questions.

    min_words : int, optional
        The minimum number of words a valid question should contain. Defaults to 15.

    max_words : int, optional
        The maximum number of words a valid question should contain. Defaults to 25.

    Returns:
    -------
    list[dict]
        A list of dictionaries containing extracted questions. Each dictionary has:
            - 'id': The episode identifier.
            - 'chunk_id': The chunk identifier.
            - 'question': The extracted question that meets the word count criteria.

    Example:
    --------
    episode = {
        'id': 1,
        'chunk_id': 101,
        'text': 'What is your name? This is an example text. Could you tell me more?'
    }
    extract_questions(episode, min_words=5, max_words=10)
    # Output: [{'id': 1, 'chunk_id': 101, 'question': 'What is your name?'}]

    Notes:
    ------
    - The function uses a regular expression to identify questions,
        defined as any sentence that ends with a "?".
    - The word count is determined by splitting the question on whitespace.
    - Only questions within the specified word range are included in the output.
    """
    questions = []

    # Find all questions in the text
    potential_questions = re.findall(r"[A-Z][^.!?]*\?", episode["text"])

    for question in potential_questions:
        # Count the words in the question
        word_count = len(question.split())

        # Add the question if it meets the minimum and maximum word count criteria
        if min_words <= word_count <= max_words:
            questions.append(
                {
                    "episode_id": episode["id"],
                    "chunk_id": episode["chunk_id"],
                    "question": question.strip(),
                }
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


def openai_rephrase(episode_questions, prompt_template_path, model="gpt-4o-mini"):
    """
    Rephrase a set of questions using OpenAI.

    Args:
        episode_questions (list): A list of questions to rephrase.
        prompt_template_path (str): Path to the prompt template.
        model (str, optional): The model to use for rephrasing. Defaults to "gpt-4o-mini".

    Returns:
        list: The rephrased questions.
    """
    prompt = build_prompt(prompt_template_path, episode_questions=episode_questions)
    response = OPENAI_CLIENT.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
    )

    # Extract and print the response
    try:
        content = parse_json_response(response.choices[0].message.content)
    except JSONDecodeError as e:
        print(e)
        print(response)
        print("\n===========================================\n")

    return content
