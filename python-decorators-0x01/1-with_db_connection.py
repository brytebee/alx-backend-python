import sqlite3 
import functools

def with_db_connection(database_name='users.db'):
    """
    Decorator that automatically handles database connection opening and closing.
    Can be used with or without a database name parameter.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Open database connection
            conn = sqlite3.connect(database_name)
            try:
                # Call the original function with connection as first argument
                result = func(conn, *args, **kwargs)
                return result
            except Exception as e:
                # Close connection on error and re-raise
                conn.close()
                raise e
            finally:
                # Always close the connection
                conn.close()
        return wrapper
    
    # Handle case where decorator is used without parentheses
    if callable(database_name):
        func = database_name
        database_name = 'users.db'
        return decorator(func)
    
    return decorator

# Example usage with default database name
@with_db_connection
def get_user_by_id(conn, user_id): 
    cursor = conn.cursor() 
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,)) 
    return cursor.fetchone() 

# Example usage with custom database name
@with_db_connection('custom_database.db')
def get_all_users(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    return cursor.fetchall()

# Example with error handling
@with_db_connection
def create_user(conn, username, email):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (username, email) VALUES (?, ?)", (username, email))
    conn.commit()
    return cursor.lastrowid

#### Fetch user by ID with automatic connection handling 
try:
    user = get_user_by_id(user_id=1)
    print(f"User found: {user}")
except Exception as e:
    print(f"Error: {e}")

# Example usage of other decorated functions
try:
    all_users = get_all_users()
    print(f"All users: {all_users}")
except Exception as e:
    print(f"Error: {e}")

try:
    new_user_id = create_user(username="john_doe", email="john@example.com")
    print(f"Created user with ID: {new_user_id}")
except Exception as e:
    print(f"Error: {e}")