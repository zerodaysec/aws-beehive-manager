import jwt
import datetime

def generate_jwt(payload, secret_key):
    """
    Generate a JWT token.

    Parameters:
    - payload (dict): Data (claims) to encode in the JWT.
    - secret_key (str): Secret key to sign the JWT.

    Returns:
    - A JWT token as a string.
    """
    # Set the expiration time for the JWT
    expiration_time = datetime.datetime.utcnow() + datetime.timedelta(hours=1)  # Token expires in 1 hour
    payload['exp'] = expiration_time

    # Encode and generate the JWT
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    return token

def verify_jwt(token, secret_key):
    """
    Verify and decode a JWT token.

    Parameters:
    - token (str): The JWT token to verify and decode.
    - secret_key (str): Secret key used to verify the JWT's signature.

    Returns:
    - The decoded payload if the token is valid, or None if it's invalid.
    """
    try:
        # Decode the token
        decoded_payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return decoded_payload
    except jwt.ExpiredSignatureError:
        print("The token has expired.")
    except jwt.InvalidTokenError:
        print("Invalid token.")

    return None

# Example usage
decoded_data = verify_jwt(token, secret_key)
if decoded_data:
    print(f"Decoded JWT data: {decoded_data}")
else:
    print("Failed to decode JWT.")


# Example usage
secret_key = 'your_secret_key_here'
user_data = {'user_id': 123, 'username': 'john_doe'}
token = generate_jwt(user_data, secret_key)
print(f"Generated JWT: {token}")
