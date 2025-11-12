import getpass
import os

from dotenv import load_dotenv, set_key

load_dotenv()


def get_key(service: str):
    service = service.upper()
    API = os.getenv(service)

    if not API:
        API = getpass.getpass(f"Service API Key: ")
        set_env_var(service, API)

    return API


def set_env_var(key: str, value: str):
    set_key(".env", key_to_set=key, value_to_set=value)


if __name__ == "__main__":
    print(get_key("COHERE"))
