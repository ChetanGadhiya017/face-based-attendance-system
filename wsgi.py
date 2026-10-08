"""Entry point:  flask --app wsgi run   |   gunicorn wsgi:app"""
from dotenv import load_dotenv

load_dotenv()

from attendance import create_app  # noqa: E402

app = create_app()
