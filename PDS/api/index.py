import os
import sys

# Add root folder to sys.path so app module is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app

app = create_app(os.environ.get('FLASK_ENV', 'production'))
