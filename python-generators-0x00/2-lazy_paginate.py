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

def lazy_paginate(page_size):
    """
    Generator that lazily loads pages of users from the database.
    
    Args:
        page_size (int): Number of users per page
        
    Yields:
        list: A page of users
    """
    offset = 0
    
    # Single loop: Continue fetching pages until no more data
    while True:
        page = paginate_users(page_size, offset)
        
        # Stop if no more data
        if not page:
            break
            
        # Yield the current page
        yield page
        
        # Move to next page
        offset += page_size

# Example usage
if __name__ == "__main__":
    print("Lazy loading paginated data...")
    
    page_size = 2
    page_count = 0
    
    try:
        for page in lazy_paginate(page_size):
            page_count += 1
            print(f"\n--- Page {page_count} ---")
            
            for user in page:
                print(f"User: {user['name']}, Email: {user['email']}, Age: {user['age']}")
        
        print(f"\nTotal pages loaded: {page_count}")
        
    except Exception as e:
        print(f"Error: {e}")