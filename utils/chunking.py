import spacy


NLP = spacy.load("en_core_web_sm")

def chunk_large_text(text, max_chunk_size=1000):
    """
    """
    doc = NLP(text)
    sentences = [sent.text for sent in doc.sents]
    
    chunks = []
    current_chunk = ""
    
    i = 0
    while i < len(sentences):
        sentence = sentences[i]
        if '?' in sentence.strip():
            # Handle the question and its following answer
            question_chunk = sentence
            i += 1
            # Include following sentences as the answer, ensuring not to exceed the max_chunk_size
            while i < len(sentences) and len(question_chunk) + len(sentences[i]) <= max_chunk_size:
                question_chunk += " " + sentences[i]
                i += 1
            # Add the combined question-answer chunk to the list
            chunks.append(question_chunk.strip())
        else:
            # If the current chunk can accommodate the sentence
            if len(current_chunk) + len(sentence) <= max_chunk_size:
                current_chunk += sentence + " "
            else:
                chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
            i += 1
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


def preindex_process_text(
    episode, 
    chunking_function,
    **chunking_function_params,
):
    """
    """
    documents = []

    if 'audio' in episode:
        del episode['audio']
    if 'description' in episode:
        del episode['description']
    if 'segments' in episode:
        del episode['segments']

    text = episode['text']
    del episode['text']

    chunks = chunking_function(
        text,
        **chunking_function_params,
    )

    for i, chunk in enumerate(chunks):
        episode_doc = episode.copy()

        episode_doc['text'] = chunk
        episode_doc['chunk_id'] = i

        documents.append(episode_doc)

    return documents