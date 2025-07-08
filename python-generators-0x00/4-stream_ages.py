import mysql.connector
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': int(os.getenv('DB_PORT', 3306)),
    'database': os.getenv('DB_NAME', 'ALX_prodev'),
    'charset': 'utf8mb4',
    'autocommit': True
}

def paginate_users(page_size, offset):
    """
    Fetches a page of users from the database.
    
    Args:
        page_size (int): Number of users per page
        offset (int): Starting position for the page
        
    Returns:
        list: List of user dictionaries for the page
    """
    connection = None
    cursor = None
    
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)
        
        # Fetch users with LIMIT and OFFSET
        query = "SELECT user_id, name, email, age FROM user_data LIMIT %s OFFSET %s"
        cursor.execute(query, (page_size, offset))
        
        return cursor.fetchall()
        
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

def stream_user_ages():
    """
    Generator that yields user ages one by one from the database.
    
    Yields:
        float: Individual user age
    """
    page_size = 100
    offset = 0
    
    # Loop 1: Iterate through pages
    while True:
        page = paginate_users(page_size, offset)
        
        # Stop if no more data
        if not page:
            break
            
        # Yield each age from the current page
        for user in page:
            yield user['age']
        
        # Move to next page
        offset += page_size

def calculate_average_age():
    """
    Calculate the average age of all users using the stream_user_ages generator.
    This function uses memory-efficient streaming without loading all data at once.
    
    Returns:
        float: Average age of all users
    """
    total_age = 0
    user_count = 0
    
    # Loop 2: Process each age from the generator
    for age in stream_user_ages():
        total_age += age
        user_count += 1
    
    # Calculate and return average
    if user_count > 0:
        return total_age / user_count
    else:
        return 0

# Example usage
if __name__ == "__main__":
    try:
        average_age = calculate_average_age()
        print(f"Average age of users: {average_age}")
        
    except Exception as e:
        print(f"Error calculating average age: {e}")