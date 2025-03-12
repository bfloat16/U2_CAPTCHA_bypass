import time
import requests
import functools

PROXIES = {
    "http": "http://127.0.0.1:7890",
    "https": "http://127.0.0.1:7890",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
}

def retry(func=None, *, max_retries=5, delay=2, exceptions=(Exception,), backoff=1):
    """
    A decorator that retries a function call in case of specified exceptions.
    
    Can be used with or without parameters:
    
    @retry
    def foo(...):
        ...
    
    or
    
    @retry(max_retries=10, delay=1, backoff=2)
    def foo(...):
        ...
    
    Parameters:
      max_retries (int): Maximum number of attempts before giving up.
      delay (int or float): Initial delay between retries in seconds.
      exceptions (tuple): Exception types that should trigger a retry.
      backoff (int or float): Factor by which the delay is multiplied after each failed attempt.
    """
    if func is None:
        # When the decorator is called with parameters
        return lambda f: retry(f, max_retries=max_retries, delay=delay, exceptions=exceptions, backoff=backoff)
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        current_delay = delay
        for attempt in range(1, max_retries + 1):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                if attempt == max_retries:
                    raise
                else:
                    print(f"[retry] Attempt {attempt} for '{func.__name__}' failed with exception: {e}. "
                          f"Retrying in {current_delay} seconds...")
                    time.sleep(current_delay)
                    current_delay *= backoff
    return wrapper

@retry  # Can be used without parentheses
def request_get_text(url):
    response = requests.get(url, proxies=PROXIES, headers=HEADERS)
    response.raise_for_status()
    return response.text

@retry()  # Or with parentheses if you prefer explicit parameters
def request_get_binary(url):
    response = requests.get(url, proxies=PROXIES, headers=HEADERS, stream=True)
    response.raise_for_status()
    return response.content

# Testing the functions when running this module directly.
if __name__ == "__main__":
    test_url = "http://httpbin.org/get"
    try:
        print("Text response from test URL:")
        print(request_get_text(test_url))
    except Exception as e:
        print("Final error after retries:", e)