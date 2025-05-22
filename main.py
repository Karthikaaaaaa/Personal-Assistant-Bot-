from utils.intent_parser import IntentParser
import json

def main():
    parser = IntentParser()
    test_inputs = [
        "Need a sunset-view table for two tonight; gluten-free menu a must",
        "Book a cab to the airport",
        "Find a gift for my friend's birthday",
        "Update my Aadhar address"
    ]

    for user_input in test_inputs:
        print(f"\nProcessing input: {user_input}")
        result = parser.process_input(user_input)
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()