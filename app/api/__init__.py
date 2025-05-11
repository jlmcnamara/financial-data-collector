# Makes 'api' a sub-package of 'app'.
# Can also be used to create the Flask app instance if structured differently.
from .routes import init_app # Expose the app factory
