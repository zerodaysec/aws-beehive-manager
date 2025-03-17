import redis

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, db=0)

# Set a key with an expiration time of 300 seconds (5 minutes)
r.setex('mykey', 300, 'myvalue')
