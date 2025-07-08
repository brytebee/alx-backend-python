import sqlite3
import functools
import logging

from datetime import datetime

# Configure logging to display INFO level messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#### decorator to log SQL queries
def log_queries(func):
    """
    Decorator that logs SQL queries before executing the decorated function.
    Assumes the first argument to the decorated function is the SQL query.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Extract the query from arguments
        # Assuming query is the first argument or a keyword argument named 'query'
        query = None
        if args:
            query = args[0]
        elif 'query' in kwargs:
            query = kwargs['query']
        
        # Log the query if found
        if query:
            print(f"{datetime} - Executing SQL query: {query}")
            logging.info(f"Executing SQL query: {query}")
        else:
            print("No query found to log")
            logging.warning("No query found to log")
        
        # Execute the original function
        return func(*args, **kwargs)
    
    return wrapper

@log_queries
def fetch_all_users(query):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    return results

#### fetch users while logging the query
users = fetch_all_users(query="SELECT * FROM users")