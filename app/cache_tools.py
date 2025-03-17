import redis
import requests
import json
from datetime import datetime, timedelta

# Connect to Redis
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

def get_cached_data(key):
    # Check if key exists in cache
    if redis_client.exists(key):
        # Return cached data
        return redis_client.get(key)
    else:
        # If key not found, query API and cache the result
        data = query_api_and_cache(key)
        return data

def query_api_and_cache(key):
    # Simulated API call
    api_url = f'https://api.example.com/{key}'
    response = requests.get(api_url)
    
    if response.status_code == 200:
        # Cache the response with expiration time set to 24 hours
        redis_client.setex(key, timedelta(days=1), response.text)
        return response.text
    else:
        return None

def list_cache_keys():
    # Get all keys in cache
    keys = redis_client.keys()
    return keys

def get_cache_value(key):
    # Get value for a specific key
    return redis_client.get(key)

def delete_cache_key(key):
    # Delete a specific key from cache
    return redis_client.delete(key)

def delete_all_cache_keys():
    # Delete all keys from cache
    return redis_client.flushdb()

if __name__ == "__main__":
    # Example usage:
    # Get cached data or query API if not found
    cached_data = get_cached_data('example_key')
    print("Cached data:", cached_data)

    # List all cache keys
    keys = list_cache_keys()
    print("Cache keys:", keys)

    # Get value for a specific key
    value = get_cache_value('example_key')
    print("Value for 'example_key':", value)

    # Delete a specific key
    delete_cache_key('example_key')

    # Delete all keys
    delete_all_cache_keys()
