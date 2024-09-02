"""
A module to preprocess huggingface dataset (YET TO BE USED)
"""


def extract_outline(text):
    """
    Used to extract outline from description, not used.
    """
    outline_started = False
    outline = []

    for line in text.split("\n"):
        if "OUTLINE:" in line:
            outline_started = True
            continue
        if outline_started:
            if line.strip() == "" or line.startswith("CONNECT:"):
                break
            outline.append(line.strip())

    return outline
