"""
"""

import os
import psycopg
from psycopg.rows import dict_row
from psycopg.errors import DatabaseError, OperationalError
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Africa/Cairo")

CREATE_STATEMENTS = {
    'conversations' : """
        CREATE TABLE conversations (
            id TEXT PRIMARY KEY,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            course TEXT NOT NULL,
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
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL
        );
    """.strip(),
    'feedback' : """
        CREATE TABLE feedback (
            id SERIAL PRIMARY KEY,
            conversation_id TEXT REFERENCES conversations(id),
            feedback INTEGER NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL
        )
    """.strip(),
}


def get_db_connection(autocommit=True, **conn_info):
    """
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
    """
    with conn.cursor() as cur:
        # Terminate all connections to the target database
        cur.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{db_name}'
                AND pid <> pg_backend_pid();
        """)
        # Drop the target database
        try:
            cur.execute(f"DROP DATABASE {db_name};")
            print(f"Database {db_name} dropped successfully.")
        except (DatabaseError, OperationalError):
            print(f"Database {db_name} doesn't exist!")


def init_db(reinit_db=False):
    """
    """
    conn_info = {
        'postgres_host':os.getenv("POSTGRES_SETUP_HOST"),
        'postgres_user':os.getenv("POSTGRES_USER"),
        'postgres_password':os.getenv("POSTGRES_PASSWORD"),
        'postgres_port':os.getenv("POSTGRES_PORT"),
    }
    postgres_db = os.getenv("POSTGRES_DB")

    ## =====> Database
    with get_db_connection(**conn_info) as conn:
        if reinit_db:
            print("Recreating Postgres DB {postgres_db}...")
            drop_db(conn, postgres_db)

        if check_database_exists(conn, postgres_db):
            print(f'Database {postgres_db} already exists')
        else:
            conn.execute(f"create database {postgres_db};")
            print(f'Successfully created database {postgres_db}')

    ## =====> Tables
    conn_info['postgres_db'] = postgres_db
    with get_db_connection(**conn_info) as conn:
        for table_name in ['conversations', 'feedback']:
            if check_table_exists(conn, table_name):
                print(f'Table {table_name} already exists')
            else:
                conn.execute(CREATE_STATEMENTS[table_name])
                print(f'Successfully created table {table_name}')


def save_conversation(conversation_id, question, answer_data, course, timestamp=None, is_setup=False):
    if timestamp is None:
        timestamp = datetime.now(TZ)

    conn_info = {
        'postgres_host':os.getenv("POSTGRES_HOST"),
        'postgres_user':os.getenv("POSTGRES_USER"),
        'postgres_password':os.getenv("POSTGRES_PASSWORD"),
        'postgres_port':os.getenv("POSTGRES_PORT"),
        'postgres_db':os.getenv("POSTGRES_DB"),
    }

    if is_setup:
        conn_info['postgres_host'] = os.getenv("POSTGRES_SETUP_HOST")
    
    with get_db_connection(**conn_info) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO conversations 
                (id, question, answer, course, model_used, response_time, relevance, 
                relevance_explanation, prompt_tokens, completion_tokens, total_tokens, 
                eval_prompt_tokens, eval_completion_tokens, eval_total_tokens, openai_cost, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, CURRENT_TIMESTAMP))
            """,
                (
                    conversation_id,
                    question,
                    answer_data["answer"],
                    course,
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


def save_feedback(conversation_id, feedback, timestamp=None, is_setup=False):
    if timestamp is None:
        timestamp = datetime.now(TZ)

    conn_info = {
        'postgres_host':os.getenv("POSTGRES_HOST"),
        'postgres_user':os.getenv("POSTGRES_USER"),
        'postgres_password':os.getenv("POSTGRES_PASSWORD"),
        'postgres_port':os.getenv("POSTGRES_PORT"),
        'postgres_db':os.getenv("POSTGRES_DB"),
    }

    if is_setup:
        conn_info['postgres_host'] = os.getenv("POSTGRES_SETUP_HOST")
    
    with get_db_connection(**conn_info) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO feedback (conversation_id, feedback, timestamp) VALUES (%s, %s, COALESCE(%s, CURRENT_TIMESTAMP))",
                (conversation_id, feedback, timestamp),
            )


def get_recent_conversations(limit=5, relevance=None):
    """
    """
    conn_info = {
        'postgres_host':os.getenv("POSTGRES_HOST"),
        'postgres_user':os.getenv("POSTGRES_USER"),
        'postgres_password':os.getenv("POSTGRES_PASSWORD"),
        'postgres_port':os.getenv("POSTGRES_PORT"),
        'postgres_db':os.getenv("POSTGRES_DB"),
    }

    with get_db_connection(**conn_info) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            query = """
                SELECT c.*, f.feedback
                FROM conversations c
                LEFT JOIN feedback f ON c.id = f.conversation_id
            """
            if relevance:
                query += f" WHERE c.relevance = '{relevance}'"
            query += " ORDER BY c.timestamp DESC LIMIT %s"

            cur.execute(query, (limit,))
            return cur.fetchall()


def get_feedback_stats():
    """
    """
    conn_info = {
        'postgres_host':os.getenv("POSTGRES_HOST"),
        'postgres_user':os.getenv("POSTGRES_USER"),
        'postgres_password':os.getenv("POSTGRES_PASSWORD"),
        'postgres_port':os.getenv("POSTGRES_PORT"),
        'postgres_db':os.getenv("POSTGRES_DB"),
    }

    with get_db_connection(**conn_info) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT 
                    SUM(CASE WHEN feedback > 0 THEN 1 ELSE 0 END) as thumbs_up,
                    SUM(CASE WHEN feedback < 0 THEN 1 ELSE 0 END) as thumbs_down
                FROM feedback
            """)
            return cur.fetchone()
