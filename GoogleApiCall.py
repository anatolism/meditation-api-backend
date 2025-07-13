import os
import google.generativeai as genai
import logging
import time
from typing import Optional
from dotenv import load_dotenv
from functools import wraps

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("GoogleApiCall.log"),
        logging.StreamHandler()
    ]
)

def retry_on_error(max_retries=3, delay=5):
    """Decorator to retry function on error with delay"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        logging.error(f"Final error after {max_retries} retries: {str(e)}")
                        raise
                    logging.warning(f"Error occurred: {str(e)}. Retry {retries}/{max_retries} in {delay} seconds...")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

class GoogleApiCall:
    """Utility class for Google API calls with retry mechanism and model configuration"""
    
    # Default model configurations
    DEFAULT_MODEL = "gemini-2.5-flash"
    MODEL_CONFIGS = {
        "gemini-2.5-flash": {
            "temperature": 0.5,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8000,
        },
        "gemini-1.0-pro-latest": {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8000,
        },
        "gemini-2.5-pro": {
            "temperature": 0.9,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8000,
        }
    }

    def __init__(self, model_name: Optional[str] = None):
        """Initialize with optional model name"""
        self.model_name = model_name or self.DEFAULT_MODEL
        self.model = None
        self._initialize_genai()

    def _initialize_genai(self) -> None:
        """Initialize the Gemini model with configuration"""
        try:
            # Load environment variables
            load_dotenv()
            api_key = os.getenv('GOOGLE_API_KEY')
            if not api_key:
                raise ValueError("GOOGLE_API_KEY environment variable not set")

            # Configure the API
            genai.configure(api_key=api_key)

            # Get model config or use default
            generation_config = self.MODEL_CONFIGS.get(
                self.model_name,
                self.MODEL_CONFIGS[self.DEFAULT_MODEL]
            )

            # Create model instance
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=generation_config
            )
            
            logging.info(f"Initialized model: {self.model_name}")

        except Exception as e:
            logging.error(f"Error initializing Generative AI: {str(e)}")
            raise

    @retry_on_error(max_retries=3, delay=5)
    def generate_content(self, message: str) -> str:
        """Generate content with retry mechanism"""
        try:
            if not self.model:
                self._initialize_genai()

            logging.info(f"Starting content generation with model {self.model_name}")
            logging.info(f"Input length: {len(message)} characters")

            response = self.model.generate_content(message)
            generated_text = response.text.strip()

            if not generated_text:
                raise ValueError("Generated content is empty")

            logging.info(f"Generated content length: {len(generated_text)} characters")
            return generated_text

        except Exception as e:
            logging.error(f"Error generating content: {str(e)}")
            raise

    @classmethod
    def get_available_models(cls) -> list:
        """Get list of available model configurations"""
        return list(cls.MODEL_CONFIGS.keys())

    @classmethod
    def add_model_config(cls, model_name: str, config: dict) -> None:
        """Add new model configuration"""
        cls.MODEL_CONFIGS[model_name] = config
        logging.info(f"Added configuration for model: {model_name}")

# Usage example:
# api_call = GoogleApiCall("gemini-2.0-pro")  # Specify model
# or
# api_call = GoogleApiCall()  # Use default model
# result = api_call.generate_content("Your prompt here")