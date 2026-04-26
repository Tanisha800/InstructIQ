import os
os.environ["GEMINI_API_KEY"] = "fake_key"
os.environ["AI_PROVIDER"] = "gemini"
import main
print("Success!")
