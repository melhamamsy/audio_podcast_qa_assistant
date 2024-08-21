"""
This module implements a Streamlit-based Lex Fridman Podcast QA application.
It provides an interface for users to ask questions answered in the podcast,
receive answers, and provide feedback on the responses.
"""

import time
import uuid

import streamlit as st

from utils.postgres import (
    get_feedback_stats,
    get_recent_conversations,
    save_conversation,
    save_feedback,
)
from utils.query import get_answer


def print_log(*message):
    """
    Print a log message with automatic flushing.

    Args:
        *message: Variable length argument list of messages to be printed.
    """
    print(*message, flush=True)


def initialize_session_state():
    """
    Initialize session state variables.

    Ensures that necessary session state variables like conversation ID,
    feedback count, and submission status are set.
    """
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = str(uuid.uuid4())
        print_log(
            f"New conversation started with ID: {st.session_state.conversation_id}"
        )
    if "count" not in st.session_state:
        st.session_state.count = 0
        print_log("Feedback count initialized to 0")
    if "submitted" not in st.session_state:
        st.session_state.submitted = False


def handle_user_input():
    """
    Handle user input and question submission.

    Returns:
        tuple: Contains title query (str), model choice (str), search type (str),
               and user question (str).
    """
    title_query = st.text_input("Enter episode title, needn't be exact (Optional):")
    print_log(f"User title query: {title_query}")
    model_choice = st.selectbox(
        "Select a model:",
        ["ollama/phi3", "openai/gpt-3.5-turbo", "openai/gpt-4o", "openai/gpt-4o-mini"],
    )
    print_log(f"User selected model: {model_choice}")
    search_type = st.radio("Select search type:", ["Text", "Vector"])
    print_log(f"User selected search type: {search_type}")
    user_input = st.text_input("Enter your question:")
    return title_query, model_choice, search_type, user_input


def process_question(user_input, title_query, model_choice, search_type):
    """
    Process the user's question and display the answer.

    Args:
        user_input (str): The question submitted by the user.
        title_query (str): The optional episode title query.
        model_choice (str): The selected model for answering the question.
        search_type (str): The search type, either 'Text' or 'Vector'.
    """
    st.session_state.question_id = str(uuid.uuid4())
    with st.spinner("Processing..."):
        start_time = time.time()
        answer_data = get_answer(user_input, title_query, model_choice, search_type)
        end_time = time.time()
        print_log(f"Answer received in {end_time - start_time:.2f} seconds")
        st.success("Completed!")
        st.write(answer_data["answer"])
        display_answer_metadata(answer_data)
        save_conversation(
            st.session_state.conversation_id,
            st.session_state.question_id,
            user_input,
            answer_data,
        )


def display_answer_metadata(answer_data):
    """
    Display metadata about the answer.

    Args:
        answer_data (dict): A dictionary containing answer metadata such as
                            episode titles, tags, response time, relevance,
                            model used, and token usage.
    """
    for i, title in enumerate(answer_data["titles"]):
        st.write(f"Episode {i+1} title: {title}")
    st.write(f"Episodes tags: {answer_data['tags']}")
    st.write(f"Response time: {answer_data['response_time']:.2f} seconds")
    st.write(f"Relevance: {answer_data['relevance']}")
    st.write(f"Model used: {answer_data['model_used']}")
    st.write(f"Total tokens: {answer_data['total_tokens']}")
    if answer_data["openai_cost"] > 0:
        st.write(f"OpenAI cost: ${answer_data['openai_cost']:.4f}")


def handle_feedback():
    """
    Handle user feedback on the answer.

    Provides buttons for positive or negative feedback and updates
    the feedback count.
    """
    col1, col2 = st.columns(2)
    with col1:
        if st.button("+1", disabled=not st.session_state.submitted):
            update_feedback(1)
    with col2:
        if st.button("-1", disabled=not st.session_state.submitted):
            update_feedback(-1)
    st.write(f"Current count: {st.session_state.count}")


def update_feedback(value):
    """
    Update feedback count and save it to the database.

    Args:
        value (int): The feedback value, either 1 (positive) or -1 (negative).
    """
    st.session_state.submitted = False
    st.session_state.count += value
    print_log(f"Feedback received. New count: {st.session_state.count}")
    save_feedback(st.session_state.conversation_id, st.session_state.question_id, value)
    print_log(f"{'Positive' if value > 0 else 'Negative'} feedback saved to database")
    st.rerun()


def display_recent_conversations():
    """
    Display recent conversations with a filtering option.

    Shows recent questions and answers with relevance and model information,
    allowing filtering by relevance.
    """
    st.subheader("Recent Conversations")
    relevance_filter = st.selectbox(
        "Filter by relevance:", ["All", "RELEVANT", "PARTLY_RELEVANT", "NON_RELEVANT"]
    )
    recent_conversations = get_recent_conversations(
        limit=5, relevance=relevance_filter if relevance_filter != "All" else None
    )
    for conv in recent_conversations:
        st.write(f"Q: {conv['question']}")
        st.write(f"A: {conv['answer']}")
        st.write(f"Relevance: {conv['relevance']}")
        st.write(f"Model: {conv['model_used']}")
        st.write("---")


def display_feedback_stats():
    """
    Display feedback statistics.

    Shows the count of positive and negative feedback received across all
    conversations.
    """
    feedback_stats = get_feedback_stats()
    st.subheader("Feedback Statistics")
    st.write(f"Thumbs up: {feedback_stats['thumbs_up']}")
    st.write(f"Thumbs down: {feedback_stats['thumbs_down']}")


def main():
    """
    Main function to run the Streamlit Lex Fridman Podcast QA application.

    This function sets up the Streamlit interface, handles user input,
    processes questions, displays answers, and manages user feedback.
    """
    print_log("Starting the Lex Fridman Podcast QA application")
    st.title("Lex Fridman Podcast QA")

    initialize_session_state()
    title_query, model_choice, search_type, user_input = handle_user_input()

    if st.button("Submit"):
        print_log(f"User submitted question: {user_input}")
        process_question(user_input, title_query, model_choice, search_type)
        st.write(f"Question submitted: {user_input}")
        st.session_state.submitted = True

    handle_feedback()
    display_recent_conversations()
    display_feedback_stats()

    print_log("Streamlit app loop completed")


if __name__ == "__main__":
    main()
