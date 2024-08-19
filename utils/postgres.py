"""
This module provides utility functions for managing PostgreSQL operations.
The utilities include functions to:
    1. Connect to the PostgreSQL database.
    2. Check the existence of databases and tables.
    3. Create, drop, and initialize databases and tables.
    4. Save conversations and feedback data.
    5. Retrieve recent conversations and feedback statistics.

These utilities streamline database operations and make it easier to handle
PostgreSQL interactions in applications.
"""

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg
from psycopg.errors import DatabaseError, OperationalError
from psycopg.rows import dict_row

from utils.variables import (POSTGRES_DB, POSTGRES_HOST, POSTGRES_PASSWORD,
                             POSTGRES_PORT, POSTGRES_USER)

TZ = ZoneInfo("Africa/Cairo")

CREATE_STATEMENTS = {
    "conversations": """
        CREATE TABLE conversations (
            id TEXT,
            question_id TEXT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            model_used TEXT NOT NULL,
            response_time FLOAT NOT NULL,
            relevance TEXT NOT NULL,
            relevance_explanation TEXT NOT NULL,
            prompt_tokens INTEGER NOT NULL,
            completion_tokens INTEGER NOT NULL,
            total_tokens INTEGER NOT NULL,
            eval_prompt_tokens INTEGER NOT NULL,
            eval_completion_tokens INTEGER NOT NULL,
            eval_total_tokens INTEGER NOT NULL,
            openai_cost FLOAT NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            PRIMARY KEY (id, question_id)
        );
    """.strip(),
    "feedback": """
        CREATE TABLE feedback (
            id SERIAL PRIMARY KEY,
            conversation_id TEXT,
            question_id TEXT,
            feedback INTEGER NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            FOREIGN KEY (conversation_id, question_id)
                REFERENCES conversations(id, question_id)
        )
    """.strip(),
}


def get_db_connection(autocommit=True, **conn_info):
    """
    Establish and return a connection to the PostgreSQL database.

    Args:
        autocommit (bool, optional): Whether to enable autocommit. Defaults to True.
        **conn_info: Connection details including host, dbname, user, password, and port.

    Returns:
        psycopg.Connection: A connection object to interact with the database.
    """
    return psycopg.connect(
        host=conn_info.get("postgres_host"),
        dbname=conn_info.get("postgres_db"),
        user=conn_info.get("postgres_user"),
        password=conn_info.get("postgres_password"),
        port=conn_info.get("postgres_port"),
        autocommit=autocommit,
    )


def check_database_exists(conn, db_name):
    """
    Check if a specified PostgreSQL database exists.

    Args:
        conn (psycopg.Connection): The connection to the PostgreSQL instance.
        db_name (str): The name of the database to check.

    Returns:
        bool: True if the database exists, otherwise False.
    """
    query = f"""
    SELECT EXISTS (
        SELECT 1 FROM pg_database WHERE datname='{db_name}'
    );
    """.strip()

    res = conn.execute(query)
    db_exists = res.fetchall()[0][0]

    return db_exists


def check_table_exists(conn, table_name):
    """
    Check if a specified table exists in the current PostgreSQL database.

    Args:
        conn (psycopg.Connection): The connection to the PostgreSQL database.
        table_name (str): The name of the table to check.

    Returns:
        bool: True if the table exists, otherwise False.
    """
    query = f"""
    SELECT EXISTS (
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = '{table_name}'
    );
    """

    res = conn.execute(query)
    table_exists = res.fetchall()[0][0]

    return bool(table_exists)


def drop_db(conn, db_name):
    """
    Drop a PostgreSQL database if it exists.

    Args:
        conn (psycopg.Connection): The connection to the PostgreSQL instance.
        db_name (str): The name of the database to drop.
    """
    with conn.cursor() as cur:
        # Terminate all connections to the target database
        cur.execute(
            f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{db_name}'
                AND pid <> pg_backend_pid();
        """
        )
        # Drop the target database
        try:
            cur.execute(f"DROP DATABASE {db_name};")
            print(f"Database {db_name} dropped successfully.")
        except (DatabaseError, OperationalError):
            print(f"Database {db_name} doesn't exist!")


def init_db(reinit_db=False):
    """
    Initialize the PostgreSQL database and create required tables.

    Args:
        reinit_db (bool, optional): Whether to recreate the database. Defaults to False.
    """
    conn_info = {
        "postgres_host": POSTGRES_HOST,
        "postgres_user": POSTGRES_USER,
        "postgres_password": POSTGRES_PASSWORD,
        "postgres_port": POSTGRES_PORT,
    }
    postgres_db = POSTGRES_DB

    ## =====> Database
    with get_db_connection(**conn_info) as conn:
        if reinit_db:
            print("Recreating Postgres DB {postgres_db}...")
            drop_db(conn, postgres_db)

        if check_database_exists(conn, postgres_db):
            print(f"Database {postgres_db} already exists")
        else:
            conn.execute(f"create database {postgres_db};")
            print(f"Successfully created database {postgres_db}")

    ## =====> Tables
    conn_info["postgres_db"] = postgres_db
    with get_db_connection(**conn_info) as conn:
        for table_name in ["conversations", "feedback"]:
            if check_table_exists(conn, table_name):
                print(f"Table {table_name} already exists")
            else:
                conn.execute(CREATE_STATEMENTS[table_name])
                print(f"Successfully created table {table_name}")


def save_conversation(
    conversation_id, question_id, question, answer_data, timestamp=None
):
    """
    Save a conversation record to the database.

    Args:
        conversation_id (str): The ID of the conversation.
        question_id (str): The ID of the question.
        question (str): The question text.
        answer_data (dict): A dictionary containing the answer and related metadata.
        timestamp (datetime, optional): The timestamp for the record. Defaults to the current time.
    """
    if timestamp is None:
        timestamp = datetime.now(TZ)

    conn_info = {
        "postgres_host": POSTGRES_HOST,
        "postgres_user": POSTGRES_USER,
        "postgres_password": POSTGRES_PASSWORD,
        "postgres_port": POSTGRES_PORT,
        "postgres_db": POSTGRES_DB,
    }

    with get_db_connection(**conn_info) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO conversations 
                (id, question_id, question, answer, model_used, response_time, relevance, 
                relevance_explanation, prompt_tokens, completion_tokens, total_tokens, 
                eval_prompt_tokens, eval_completion_tokens, eval_total_tokens, 
                openai_cost, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                COALESCE(%s, CURRENT_TIMESTAMP))
            """,
                (
                    conversation_id,
                    question_id,
                    question,
                    answer_data["answer"],
                    answer_data["model_used"],
                    answer_data["response_time"],
                    answer_data["relevance"],
                    answer_data["relevance_explanation"],
                    answer_data["prompt_tokens"],
                    answer_data["completion_tokens"],
                    answer_data["total_tokens"],
                    answer_data["eval_prompt_tokens"],
                    answer_data["eval_completion_tokens"],
                    answer_data["eval_total_tokens"],
                    answer_data["openai_cost"],
                    timestamp,
                ),
            )


def save_feedback(conversation_id, question_id, feedback, timestamp=None):
    """
    Save feedback for a conversation to the database.

    Args:
        conversation_id (str): The ID of the conversation.
        question_id (str): The ID of the question.
        feedback (int): The feedback value (e.g., +1 for positive, -1 for negative).
        timestamp (datetime, optional): The timestamp for the feedback.
        Defaults to the current time.
    """
    if timestamp is None:
        timestamp = datetime.now(TZ)

    conn_info = {
        "postgres_host": POSTGRES_HOST,
        "postgres_user": POSTGRES_USER,
        "postgres_password": POSTGRES_PASSWORD,
        "postgres_port": POSTGRES_PORT,
        "postgres_db": POSTGRES_DB,
    }

    with get_db_connection(**conn_info) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO feedback (conversation_id, question_id, feedback, timestamp) 
                VALUES (%s, %s, %s, COALESCE(%s, CURRENT_TIMESTAMP))""",
                (conversation_id, question_id, feedback, timestamp),
            )


def get_recent_conversations(limit=5, relevance=None):
    """
    Retrieve recent conversations from the database with optional relevance filtering.

    Args:
        limit (int, optional): The maximum number of conversations to retrieve. Defaults to 5.
        relevance (str, optional): The relevance filter (e.g., 'RELEVANT'). Defaults to None.

    Returns:
        list of dict: A list of conversation records with feedback information.
    """
    conn_info = {
        "postgres_host": os.getenv("POSTGRES_HOST"),
        "postgres_user": os.getenv("POSTGRES_USER"),
        "postgres_password": os.getenv("POSTGRES_PASSWORD"),
        "postgres_port": os.getenv("POSTGRES_PORT"),
        "postgres_db": os.getenv("POSTGRES_DB"),
    }

    with get_db_connection(**conn_info) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            query = """
                SELECT c.*, f.feedback
                FROM conversations c
                LEFT JOIN feedback f ON c.id = f.conversation_id
                AND c.question_id = f.question_id
            """
            if relevance:
                query += f" WHERE c.relevance = '{relevance}'"
            query += " ORDER BY c.timestamp DESC LIMIT %s"

            cur.execute(query, (limit,))
            return cur.fetchall()


def get_feedback_stats():
    """
    Retrieve feedback statistics, including counts of positive and negative feedback.

    Returns:
        dict: A dictionary with counts of 'thumbs_up' and 'thumbs_down'.
    """
    conn_info = {
        "postgres_host": os.getenv("POSTGRES_HOST"),
        "postgres_user": os.getenv("POSTGRES_USER"),
        "postgres_password": os.getenv("POSTGRES_PASSWORD"),
        "postgres_port": os.getenv("POSTGRES_PORT"),
        "postgres_db": os.getenv("POSTGRES_DB"),
    }

    with get_db_connection(**conn_info) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT 
                    SUM(CASE WHEN feedback > 0 THEN 1 ELSE 0 END) as thumbs_up,
                    SUM(CASE WHEN feedback < 0 THEN 1 ELSE 0 END) as thumbs_down
                FROM feedback
            """
            )
            return cur.fetchone()
