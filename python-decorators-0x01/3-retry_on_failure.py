import time
import sqlite3 
import functools
import logging

# Configure logging to see retry attempts
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

def retry_on_failure(retries=3, delay=2, backoff_factor=1.5):
    """
    Decorator that retries a function if it fails due to exceptions.
    
    Args:
        retries (int): Maximum number of retry attempts (default: 3)
        delay (float): Initial delay between retries in seconds (default: 2)
        backoff_factor (float): Multiplier for delay after each retry (default: 1.5)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(retries + 1):  # +1 to include the initial attempt
                try:
                    # Attempt to execute the function
                    result = func(*args, **kwargs)
                    
                    # If we get here, the function succeeded
                    if attempt > 0:
                        logging.info(f"Function '{func.__name__}' succeeded on attempt {attempt + 1}")
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    # If this was the last attempt, raise the exception
                    if attempt == retries:
                        logging.error(f"Function '{func.__name__}' failed after {retries + 1} attempts. Final error: {e}")
                        raise e
                    
                    # Log the retry attempt
                    logging.warning(f"Function '{func.__name__}' failed on attempt {attempt + 1}, retrying in {current_delay}s. Error: {e}")
                    
                    # Wait before retrying
                    time.sleep(current_delay)
                    
                    # Increase delay for next retry (exponential backoff)
                    current_delay *= backoff_factor
            
            # This should never be reached, but just in case
            raise last_exception
            
        return wrapper
    return decorator

# Enhanced version that only retries on specific database errors
def retry_on_db_failure(retries=3, delay=2, backoff_factor=1.5):
    """
    Decorator that retries a function only on specific database-related exceptions.
    More targeted than retry_on_failure for database operations.
    """
    # Define transient database errors that are worth retrying
    TRANSIENT_ERRORS = (
        sqlite3.OperationalError,  # Database is locked, etc.
        sqlite3.DatabaseError,    # General database errors
        ConnectionError,          # Network-related issues
        TimeoutError,            # Timeout issues
    )
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(retries + 1):
                try:
                    result = func(*args, **kwargs)
                    
                    if attempt > 0:
                        logging.info(f"Database operation '{func.__name__}' succeeded on attempt {attempt + 1}")
                    
                    return result
                    
                except TRANSIENT_ERRORS as e:
                    last_exception = e
                    
                    if attempt == retries:
                        logging.error(f"Database operation '{func.__name__}' failed after {retries + 1} attempts. Final error: {e}")
                        raise e
                    
                    logging.warning(f"Transient database error in '{func.__name__}' on attempt {attempt + 1}, retrying in {current_delay}s. Error: {e}")
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
                    
                except Exception as e:
                    # For non-transient errors, don't retry
                    logging.error(f"Non-transient error in '{func.__name__}': {e}")
                    raise e
            
            raise last_exception
            
        return wrapper
    return decorator

# Example usage with basic retry
@with_db_connection
@retry_on_failure(retries=3, delay=1)
def fetch_users_with_retry(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    return cursor.fetchall()

# Example usage with database-specific retry
@with_db_connection
@retry_on_db_failure(retries=5, delay=0.5)
def fetch_user_by_id_with_db_retry(conn, user_id):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cursor.fetchone()

# Example that simulates intermittent failures for testing
@with_db_connection
@retry_on_failure(retries=3, delay=1)
def flaky_database_operation(conn):
    """Simulates a flaky database operation for testing retry logic"""
    import random
    cursor = conn.cursor()
    
    # Simulate intermittent failures
    if random.random() < 0.6:  # 60% chance of failure
        raise sqlite3.OperationalError("Database is locked")
    
    cursor.execute("SELECT COUNT(*) FROM users")
    return cursor.fetchone()[0]

#### Attempt to fetch users with automatic retry on failure
try:
    users = fetch_users_with_retry()
    print(f"Successfully fetched {len(users) if users else 0} users")
except Exception as e:
    print(f"Failed to fetch users: {e}")

# Example of targeted database retry
try:
    user = fetch_user_by_id_with_db_retry(user_id=1)
    print(f"Successfully fetched user: {user}")
except Exception as e:
    print(f"Failed to fetch user: {e}")

# Example of flaky operation (uncomment to test retry behavior)
# try:
#     count = flaky_database_operation()
#     print(f"User count: {count}")
# except Exception as e:
#     print(f"Flaky operation failed: {e}")