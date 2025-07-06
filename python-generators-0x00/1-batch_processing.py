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

def stream_users_in_batches(batch_size):
    """
    Generator function that fetches rows from the user_data table in batches.
    
    Args:
        batch_size (int): Number of rows to fetch in each batch
        
    Yields:
        list: A list of dictionaries containing user data for each batch
    """
    connection = None
    cursor = None
    
    try:
        # Connect to the database
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)
        
        # Execute query to fetch all users
        cursor.execute("SELECT user_id, name, email, age FROM user_data")
        
        # Loop 1: Fetch and yield rows in batches
        while True:
            # Fetch a batch of rows
            batch = cursor.fetchmany(batch_size)
            
            # If no more rows, break the loop
            if not batch:
                break
                
            # Yield the current batch
            yield batch
            
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

def batch_processing(batch_size):
    """
    Generator function that processes each batch to filter users over the age of 25.
    
    Args:
        batch_size (int): Number of rows to process in each batch
        
    Yields:
        list: A list of users over 25 years old from each batch
    """
    # Loop 2: Process each batch from the stream_users_in_batches generator
    for batch in stream_users_in_batches(batch_size):
        # Filter users over 25 years old
        filtered_users = []
        
        # Loop 3: Filter users in the current batch
        for user in batch:
            if user['age'] > 25:
                filtered_users.append(user)
        
        # Yield the filtered batch (only if it contains users)
        if filtered_users:
            yield filtered_users

# Example usage and testing
if __name__ == "__main__":
    print("Processing users in batches (filtering age > 25)...")
    
    batch_size = 2  # Process 2 users at a time
    
    try:
        # Test the batch processing generator
        batch_count = 0
        total_users_processed = 0
        
        for filtered_batch in batch_processing(batch_size):
            batch_count += 1
            print(f"\n--- Batch {batch_count} (Users over 25) ---")
            
            for user in filtered_batch:
                total_users_processed += 1
                print(f"User: {user['name']}, Email: {user['email']}, Age: {user['age']}")
        
        print(f"\n📊 Summary:")
        print(f"Total batches processed: {batch_count}")
        print(f"Total users over 25: {total_users_processed}")
        
    except Exception as e:
        print(f"Error processing batches: {e}")