import mysql.connector
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Database configuration using environment variables
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': int(os.getenv('DB_PORT', 3306)),
    'database': os.getenv('DB_NAME', 'ALX_prodev'),
    'charset': 'utf8mb4',
    'autocommit': True
}

def stream_users():
    """
    Generator function that streams rows from the user_data table one by one.
    
    Yields:
        dict: A dictionary containing user data for each row
    """
    connection = None
    cursor = None
    
    try:
        # Connect to the database
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)  # Return results as dictionaries
        
        # Execute query to fetch all users
        cursor.execute("SELECT user_id, name, email, age FROM user_data")
        
        # Use a single loop to fetch and yield rows one by one
        for row in cursor:
            yield row
            
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
        return
    except Exception as e:
        print(f"Unexpected error: {e}")
        return
    finally:
        # Clean up resources
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

# Example usage and testing
if __name__ == "__main__":
    print("Streaming users from database...")
    
    # Test the generator
    try:
        for user in stream_users():
            print(f"User: {user['name']}, Email: {user['email']}, Age: {user['age']}")
    except Exception as e:
        print(f"Error streaming users: {e}")