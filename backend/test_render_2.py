import os
os.environ.clear() # Clear all env vars
os.environ["GEMINI_API_KEY"] = "fake_key"
os.environ["AI_PROVIDER"] = "gemini"
import main
print("Success!")
