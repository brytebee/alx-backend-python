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

def transactional(func):
    """
    Decorator that manages database transactions.
    Automatically commits on success or rolls back on error.
    Assumes the first argument is a database connection.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Get the connection (first argument)
        if not args:
            raise ValueError("Transactional decorator requires a database connection as first argument")
        
        conn = args[0]
        
        try:
            # Execute the function
            result = func(*args, **kwargs)
            # If no exception occurred, commit the transaction
            conn.commit()
            return result
        except Exception as e:
            # If an exception occurred, rollback the transaction
            conn.rollback()
            raise e  # Re-raise the exception
    
    return wrapper

# Example usage with both decorators
@with_db_connection 
@transactional 
def update_user_email(conn, user_id, new_email): 
    cursor = conn.cursor() 
    cursor.execute("UPDATE users SET email = ? WHERE id = ?", (new_email, user_id)) 
    # Simulate an error condition (uncomment to test rollback)
    # if new_email == 'test@error.com':
    #     raise ValueError("Invalid email format")

# Example of a more complex transaction with multiple operations
@with_db_connection
@transactional
def transfer_user_credits(conn, from_user_id, to_user_id, amount):
    """Example of a complex transaction with multiple operations"""
    cursor = conn.cursor()
    
    # Check if from_user has enough credits
    cursor.execute("SELECT credits FROM users WHERE id = ?", (from_user_id,))
    from_user_credits = cursor.fetchone()
    
    if not from_user_credits or from_user_credits[0] < amount:
        raise ValueError("Insufficient credits")
    
    # Deduct credits from source user
    cursor.execute("UPDATE users SET credits = credits - ? WHERE id = ?", (amount, from_user_id))
    
    # Add credits to destination user
    cursor.execute("UPDATE users SET credits = credits + ? WHERE id = ?", (amount, to_user_id))
    
    # Both operations will be committed together or rolled back together

# Example usage showing error handling
@with_db_connection
@transactional
def batch_update_users(conn, user_updates):
    """Example showing batch operations in a transaction"""
    cursor = conn.cursor()
    
    for user_id, new_email in user_updates:
        cursor.execute("UPDATE users SET email = ? WHERE id = ?", (new_email, user_id))
        # If any update fails, all updates will be rolled back

#### Update user's email with automatic transaction handling 
try:
    update_user_email(user_id=1, new_email='Crawford_Cartwright@hotmail.com')
    print("User email updated successfully")
except Exception as e:
    print(f"Error updating user email: {e}")

# Example of successful transaction
try:
    transfer_user_credits(from_user_id=1, to_user_id=2, amount=100)
    print("Credits transferred successfully")
except Exception as e:
    print(f"Error transferring credits: {e}")

# Example of batch update
try:
    updates = [(1, 'user1@example.com'), (2, 'user2@example.com')]
    batch_update_users(user_updates=updates)
    print("Batch update completed successfully")
except Exception as e:
    print(f"Error in batch update: {e}")