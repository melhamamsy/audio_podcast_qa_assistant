"""
"""

from collections import defaultdict


def extract_questions(
    episode,
    min_words = 11,
):
    """
    """
    questions = []
    epidose_id = episode['id']
    
    for segment in episode['segments']:
        if '?' == segment['text'][-1]:
            segment_text_list = segment['text'].split()
            if segment_text_list[0].istitle():
                if len(segment_text_list) >= min_words:
                    questions.append(
                        {
                            "episode_id": epidose_id,
                            "question": segment['text']
                        }
                    )
                
    return questions


def group_questions_by_episode(questions):
    """
    """
    questions_per_episode = defaultdict(list)
    for question in questions:
        questions_per_episode[question['episode_id']].append(question)

    questions_per_episode = list(questions_per_episode.values())
    return questions_per_episode