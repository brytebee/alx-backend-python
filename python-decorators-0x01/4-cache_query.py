import time
import sqlite3 
import functools
import hashlib
import json
import logging

# Configure logging to see cache hits/misses
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

query_cache = {}

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

def cache_query(func):
    """
    Decorator that caches query results based on the SQL query string and parameters.
    Supports both positional and keyword arguments for query parameters.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Generate a cache key based on function name, args, and kwargs
        cache_key = _generate_cache_key(func.__name__, args, kwargs)
        
        # Check if result is already cached
        if cache_key in query_cache:
            logging.info(f"Cache HIT for query in '{func.__name__}'")
            return query_cache[cache_key]['result']
        
        # Execute the function and cache the result
        logging.info(f"Cache MISS for query in '{func.__name__}' - executing query")
        result = func(*args, **kwargs)
        
        # Store in cache with timestamp
        query_cache[cache_key] = {
            'result': result,
            'timestamp': time.time(),
            'function': func.__name__
        }
        
        return result
    
    return wrapper

def cache_query_with_ttl(ttl_seconds=300):
    """
    Advanced caching decorator with Time-To-Live (TTL) support.
    
    Args:
        ttl_seconds (int): Time in seconds after which cached results expire (default: 300 = 5 minutes)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = _generate_cache_key(func.__name__, args, kwargs)
            current_time = time.time()
            
            # Check if result is cached and not expired
            if cache_key in query_cache:
                cache_entry = query_cache[cache_key]
                if current_time - cache_entry['timestamp'] < ttl_seconds:
                    logging.info(f"Cache HIT for query in '{func.__name__}' (age: {current_time - cache_entry['timestamp']:.1f}s)")
                    return cache_entry['result']
                else:
                    logging.info(f"Cache EXPIRED for query in '{func.__name__}' - removing from cache")
                    del query_cache[cache_key]
            
            # Execute the function and cache the result
            logging.info(f"Cache MISS for query in '{func.__name__}' - executing query")
            result = func(*args, **kwargs)
            
            query_cache[cache_key] = {
                'result': result,
                'timestamp': current_time,
                'function': func.__name__
            }
            
            return result
        
        return wrapper
    return decorator

def _generate_cache_key(func_name, args, kwargs):
    """
    Generate a unique cache key based on function name, arguments, and keyword arguments.
    Excludes the database connection from the key generation.
    """
    # Skip the first argument (database connection) for key generation
    cache_args = args[1:] if len(args) > 1 else ()
    
    # Create a dictionary of all parameters for consistent key generation
    key_data = {
        'function': func_name,
        'args': cache_args,
        'kwargs': kwargs
    }
    
    # Convert to JSON string for consistent ordering
    key_string = json.dumps(key_data, sort_keys=True, default=str)
    
    # Generate MD5 hash for shorter key
    return hashlib.md5(key_string.encode()).hexdigest()

def clear_query_cache():
    """Utility function to clear all cached queries"""
    global query_cache
    cache_count = len(query_cache)
    query_cache.clear()
    logging.info(f"Cleared {cache_count} entries from query cache")

def get_cache_stats():
    """Utility function to get cache statistics"""
    if not query_cache:
        return "Cache is empty"
    
    stats = {
        'total_entries': len(query_cache),
        'functions': {},
        'oldest_entry': None,
        'newest_entry': None
    }
    
    timestamps = []
    for entry in query_cache.values():
        func_name = entry['function']
        timestamp = entry['timestamp']
        
        if func_name not in stats['functions']:
            stats['functions'][func_name] = 0
        stats['functions'][func_name] += 1
        
        timestamps.append(timestamp)
    
    if timestamps:
        stats['oldest_entry'] = time.time() - min(timestamps)
        stats['newest_entry'] = time.time() - max(timestamps)
    
    return stats

# Example usage with basic caching
@with_db_connection
@cache_query
def fetch_users_with_cache(conn, query):
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()

# Example usage with TTL caching
@with_db_connection
@cache_query_with_ttl(ttl_seconds=60)  # Cache for 1 minute
def fetch_user_by_id_with_ttl(conn, user_id):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cursor.fetchone()

# Example with parameterized queries
@with_db_connection
@cache_query
def fetch_users_by_status_with_cache(conn, status, limit=10):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE status = ? LIMIT ?", (status, limit))
    return cursor.fetchall()

# Example showing cache behavior
@with_db_connection
@cache_query
def slow_complex_query(conn, min_age, max_age):
    """Simulate a slow, complex query that benefits from caching"""
    cursor = conn.cursor()
    # Simulate processing time
    time.sleep(1)  # Remove this in real usage
    cursor.execute("""
        SELECT u.*, COUNT(o.id) as order_count 
        FROM users u 
        LEFT JOIN orders o ON u.id = o.user_id 
        WHERE u.age BETWEEN ? AND ? 
        GROUP BY u.id
    """, (min_age, max_age))
    return cursor.fetchall()

#### First call will cache the result
print("=== First call (will cache) ===")
users = fetch_users_with_cache(query="SELECT * FROM users")
print(f"Fetched {len(users) if users else 0} users")

#### Second call will use the cached result
print("\n=== Second call (from cache) ===")
users_again = fetch_users_with_cache(query="SELECT * FROM users")
print(f"Fetched {len(users_again) if users_again else 0} users")

# Example with different parameters (will not use cache)
print("\n=== Different query (new cache entry) ===")
try:
    active_users = fetch_users_by_status_with_cache(status="active", limit=5)
    print(f"Fetched {len(active_users) if active_users else 0} active users")
except Exception as e:
    print(f"Error: {e}")

# Example with same parameters (will use cache)
print("\n=== Same query again (from cache) ===")
try:
    active_users_cached = fetch_users_by_status_with_cache(status="active", limit=5)
    print(f"Fetched {len(active_users_cached) if active_users_cached else 0} active users")
except Exception as e:
    print(f"Error: {e}")

# Show cache statistics
print("\n=== Cache Statistics ===")
stats = get_cache_stats()
print(f"Cache stats: {stats}")

# Example of TTL caching
print("\n=== TTL Caching Example ===")
try:
    user = fetch_user_by_id_with_ttl(user_id=1)
    print(f"User: {user}")
    
    # Immediate second call (from cache)
    user_cached = fetch_user_by_id_with_ttl(user_id=1)
    print(f"User cached: {user_cached}")
except Exception as e:
    print(f"Error: {e}")

# Utility functions demonstration
print("\n=== Cache Management ===")
print(f"Current cache size: {len(query_cache)}")
# clear_query_cache()  # Uncomment to clear cache