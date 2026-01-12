import google.generativeai as genai
import sys

def test_gemini(api_key):
    try:
        genai.configure(api_key=api_key)
        print("--- Available Models ---")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"Model: {m.name}")
        
        print("\n--- Testing Generation with gemini-1.5-flash ---")
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Say hello")
        print(f"Response: {response.text}")
        print("\nSUCCESS: API is working and model found.")
    except Exception as e:
        print(f"\nFAILURE: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_ai.py YOUR_API_KEY")
    else:
        test_gemini(sys.argv[1])
