from langgraph.graph import StateGraph, END
from typing import TypedDict, Dict, List
from services.llm_service import LLMService
from services.search_service import SearchService
from datetime import datetime, timedelta
import re
import json

class State(TypedDict):
    user_input: str
    intents: List[Dict]  # List of intents with category, confidence, key_entities, follow_up_questions
    web_search_results: List[Dict]

def normalize_date(date_str: str, current_date: datetime) -> str:
    """Normalize date strings, validate feasibility, and handle non-English terms."""
    date_str = date_str.lower().strip()
    # Correct common misspellings
    misspellings = {
        "tonite": "tonight",
        "tmrw": "tomorrow",
        "tommorow": "tomorrow",
        "restraunt": "restaurant",
        "itlian": "Italian",
        "febuary": "february"
    }
    for misspelled, correct in misspellings.items():
        date_str = date_str.replace(misspelled, correct)

    # Resolve relative dates
    today = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
    if date_str in ["today", "tonight"]:
        return today.strftime("%Y-%m-%d")
    elif date_str == "tomorrow":
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    elif date_str == "a week from now":
        return (today + timedelta(days=7)).strftime("%Y-%m-%d")
    elif date_str == "next week":
        return "ambiguous_next_week"  # Flag for follow-up
    elif date_str == "yesterday":
        return "invalid_past_date"  # Flag for follow-up
    elif "next" in date_str:
        # Handle "next Monday", "next Tuesday", etc.
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for day in days:
            if f"next {day}" in date_str:
                current_dow = today.weekday()
                target_dow = days.index(day)
                days_ahead = (target_dow - current_dow + 7) % 7 or 7
                return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    
    # Validate specific dates
    try:
        # Clean up the date string
        date_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)  # Remove ordinal indicators
        
        # Try parsing common date formats
        date_formats = [
            "%B %d %Y",  # February 23 2025
            "%d %B %Y",  # 23 February 2025
            "%B %d, %Y",  # February 23, 2025
            "%d %B, %Y",  # 23 February, 2025
            "%Y-%m-%d",  # 2025-02-23
            "%d-%m-%Y",  # 23-02-2025
            "%m-%d-%Y",  # 02-23-2025
            "%d/%m/%Y",  # 23/02/2025
            "%m/%d/%Y",  # 02/23/2025
            "%Y/%m/%d"   # 2025/02/23
        ]
        
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                if parsed_date < today:
                    return "invalid_past_date"
                return parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                continue
                
        return "invalid_date"  # Flag for follow-up if no format matches
    except Exception:
        return "invalid_date"  # Flag for follow-up if any other error occurs

class IntentParser:
    def __init__(self):
        self.llm_service = LLMService()
        self.search_service = SearchService()
        self.graph = self._build_graph()
        self.current_date = datetime.now()  # Current date: May 22, 2025, 05:36 PM IST
        # Define offensive keywords for filtering
        self.offensive_keywords = [
        ]#please include offensive words here.
        # Define impossible/fictional locations
        self.invalid_locations = [
        ]#please add invalid locations here, like Moon, Mars, Narnia, etc

    def _build_graph(self):
        graph = StateGraph(State)
        graph.add_node("parse_intent", self._parse_intent)
        graph.add_node("extract_entities", self._extract_entities)
        graph.add_node("generate_follow_ups", self._generate_follow_ups)
        graph.add_node("handle_non_standard", self._handle_non_standard)
        graph.add_edge("parse_intent", "extract_entities")
        graph.add_edge("extract_entities", "generate_follow_ups")
        graph.add_conditional_edges(
            "generate_follow_ups",
            lambda state: "handle_non_standard" if any(intent["category"] == "other" for intent in state["intents"]) else END,
            {"handle_non_standard": "handle_non_standard", END: END}
        )
        graph.set_entry_point("parse_intent")
        return graph.compile()

    def _is_offensive(self, user_input: str) -> bool:
        """Check if input contains offensive language."""
        if not isinstance(user_input, str):
            return False  # Avoid type errors
        input_lower = user_input.lower()
        return any(keyword in input_lower for keyword in self.offensive_keywords)

    def _parse_intent(self, state: State) -> State:
        user_input = state["user_input"]
        if not isinstance(user_input, str):
            return {
                **state,
                "intents": [{"category": "other", "confidence": 0.5, "follow_up_questions": ["Could you provide a valid request?"]}]
            }
        prompt = f"""
        Identify the primary intent in the following user input, focusing on the main action (e.g., 'book', 'find', 'suggest'). Possible categories: dining, travel, gifting, cab_booking, other.
        Only identify multiple intents if distinct actions are mentioned (e.g., 'book a flight and a dinner'). Any action not related to dining, travel, gifting, or cab_booking (e.g., hotel booking, suggestions like 'suggest a dress' or 'suggest a book', or 'update Aadhar') should be classified as 'other'.
        For suggestion requests (e.g., 'suggest a dress', 'suggest a book'), classify as 'other' unless explicitly tied to gift-giving (e.g., 'suggest a gift for my wife'). If the suggestion is for personal use (e.g., 'for me') or unspecified, use 'other'.
        If multiple travel intents are mentioned (e.g., 'book a flight to Paris and a flight to London'), flag as conflicting.
        For each intent, provide a confidence score (0.0 to 1.0).
        Input: {user_input}
        Output format: ```json
        [{{"category": "<category>", "confidence": <score>, "conflict": "<optional conflict message>"}}, ...]
        ```
        """
        try:
            response = self.llm_service.generate_response(prompt)
            intents = json.loads(response.strip("```json\n").strip("```"))
        except (json.JSONDecodeError, ValueError):
            # Handle malformed LLM response
            intents = [{"category": "other", "confidence": 0.5}]
        # Initialize follow_up_questions for each intent
        for intent in intents:
            intent["follow_up_questions"] = []
            intent.setdefault("conflict", "")
        return {**state, "intents": intents}

    def _extract_entities(self, state: State) -> State:
        user_input = state["user_input"]
        intents = state["intents"]
        for intent in intents:
            category = intent["category"]
            prompt = f"""
            Extract key entities from the following user input for the intent category '{category}'.
            Entities to extract (if applicable): date, time, location, cuisine, dietary, preference, party_size, budget, destination, pickup_location, occasion, recipient, topic.
            Check for contradictions (e.g., 'cheap' and 'luxury') and flag them.
            Validate party_size (flag if > 100) and locations (flag if fictional/impossible like 'moon', 'Narnia').
            Input: {user_input}
            Output format: ```json
            {{"entities": {{}}, "contradictions": [], "validation_errors": []}}
            ```
            """
            try:
                response = self.llm_service.generate_response(prompt)
                result = json.loads(response.strip("```json\n").strip("```"))
            except (json.JSONDecodeError, ValueError):
                result = {"entities": {"topic": "unknown"}, "contradictions": [], "validation_errors": ["Invalid response from LLM"]}
            
            # Normalize date entities
            if "date" in result["entities"]:
                result["entities"]["date"] = normalize_date(result["entities"]["date"], self.current_date)
            
            # Validate party_size
            if "party_size" in result["entities"]:
                try:
                    party_size = int(result["entities"]["party_size"])
                    if party_size > 100:
                        result["validation_errors"].append("Party size seems unusually large")
                except ValueError:
                    result["validation_errors"].append("Invalid party size format")
            
            # Validate locations
            for loc_key in ["location", "destination", "pickup_location"]:
                if loc_key in result["entities"]:
                    loc = str(result["entities"][loc_key]).lower()
                    if any(invalid in loc for invalid in self.invalid_locations):
                        result["validation_errors"].append(f"Invalid {loc_key}: {loc}")
            
            intent["key_entities"] = result["entities"]
            intent["contradictions"] = result["contradictions"]
            intent["validation_errors"] = result.get("validation_errors", [])
        return state

    def _generate_follow_ups(self, state: State) -> State:
        for intent in state["intents"]:
            category = intent["category"]
            entities = intent["key_entities"]
            contradictions = intent.get("contradictions", [])
            validation_errors = intent.get("validation_errors", [])
            conflict = intent.get("conflict", "")
            follow_ups = []

            # Handle contradictions
            if contradictions:
                follow_ups.append(f"Could you clarify your request regarding {', '.join(contradictions)}?")

            # Handle conflicts
            if conflict:
                follow_ups.append(f"Could you clarify your request? {conflict}")

            # Handle validation errors
            for error in validation_errors:
                if "Party size" in error:
                    follow_ups.append("Could you confirm the party size? It seems unusually large.")
                elif "Invalid date" in error or "past date" in error:
                    follow_ups.append("Could you specify a valid future date for your request?")
                elif "Invalid location" in error or "Invalid destination" in error or "Invalid pickup_location" in error:
                    follow_ups.append("Could you specify a real location or destination?")

            if category == "dining":
                if not entities.get("party_size"):
                    follow_ups.append("How many people are dining?")
                if not entities.get("location"):
                    follow_ups.append("Could you specify the city or location for the restaurant?")
                if not entities.get("cuisine"):
                    follow_ups.append("Do you have a preferred cuisine type?")
                if not entities.get("budget"):
                    follow_ups.append("What is your budget for the meal?")
                if not entities.get("date"):
                    follow_ups.append("What date would you like to make the reservation for?")
                elif entities.get("date") == "ambiguous_next_week":
                    follow_ups.append("Which day next week would you like to dine?")
                elif entities.get("date") and not entities.get("time"):
                    follow_ups.append("What time would you like to dine?")
                if entities.get("date") in ["today", "tonight", "tomorrow", "a week from now"]:
                    follow_ups.append("Could you confirm the specific date and time for your reservation?")
            elif category == "travel":
                if not entities.get("destination"):
                    follow_ups.append("Where are you planning to travel?")
                else:
                    if entities.get("destination").lower() in ["airport", "station"]:
                        follow_ups.append(f"Which {entities['destination'].lower()} are you referring to?")
                if not entities.get("party_size"):
                    follow_ups.append("How many people are traveling?")
                if not entities.get("budget"):
                    follow_ups.append("What is your budget for the trip?")
                if not entities.get("date"):
                    follow_ups.append("When are you planning to travel?")
                elif entities.get("date") == "ambiguous_next_week":
                    follow_ups.append("Which day next week would you like to travel?")
                elif entities.get("date") and not entities.get("time"):
                    follow_ups.append("What time would you like to travel?")
                if entities.get("date") in ["today", "tonight", "tomorrow", "a week from now"]:
                    follow_ups.append("Could you confirm the specific date and time for your travel?")
            elif category == "cab_booking":
                if not entities.get("pickup_location"):
                    if entities.get("destination", "").lower() == "airport":
                        follow_ups.append("Which airport are you departing from?")
                    else:
                        follow_ups.append("What is your pickup location?")
                elif entities.get("pickup_location").lower() in ["airport"] or (
                    entities.get("pickup_location") == entities.get("destination")
                ):
                    follow_ups.append("Which airport or location are you departing from?")
                if not entities.get("destination"):
                    follow_ups.append("What is your destination?")
                elif entities.get("destination").lower() in ["airport"] or (
                    entities.get("pickup_location") == entities.get("destination")
                ):
                    follow_ups.append("Which airport or location are you going to?")
                if not entities.get("time"):
                    follow_ups.append("When do you need the cab?")
                elif entities.get("date") and not entities.get("time"):
                    follow_ups.append("What time do you need the cab?")
                if entities.get("date") in ["today", "tonight", "tomorrow", "a week from now"]:
                    follow_ups.append("Could you confirm the specific date and time for your cab?")
                if not entities.get("budget"):
                    follow_ups.append("Do you have a preferred cab type or budget?")
            elif category == "gifting":
                if not entities.get("budget"):
                    follow_ups.append("What is your budget for the gift?")
                if not entities.get("occasion"):
                    follow_ups.append("What is the occasion for the gift?")
                if entities.get("recipient") and entities["recipient"] not in ["unknown", ""]:
                    follow_ups.append(f"What are some interests or preferences of your {entities['recipient']}?")
                elif not entities.get("recipient"):
                    follow_ups.append("Who is the gift for (e.g., friend, family, colleague)?")
            elif category == "other":
                topic = entities.get("topic", "").lower()
                if "hotel" in topic or "accommodation" in topic:
                    if not entities.get("destination"):
                        follow_ups.append("Where are you planning to book a hotel?")
                    if not entities.get("party_size"):
                        follow_ups.append("How many people will be staying?")
                    if not entities.get("budget"):
                        follow_ups.append("What is your budget for the hotel?")
                    if not entities.get("date"):
                        follow_ups.append("When are you planning to check in?")
                    elif entities.get("date") == "ambiguous_next_week":
                        follow_ups.append("Which day next week would you like to check in?")
                    elif entities.get("date") and not entities.get("time"):
                        follow_ups.append("What time will you check in?")
                    if entities.get("date") in ["today", "tonight", "tomorrow", "a week from now"]:
                        follow_ups.append("Could you confirm the specific check-in date and time?")
                elif "aadhar" in topic:
                    follow_ups.append("Do you have your Aadhar number ready?")
                    follow_ups.append("Are you updating your address online or at a physical center?")
                elif "book" in topic or "reading" in topic:
                    follow_ups.append("What type of book are you looking for (e.g., genre, fiction/non-fiction)?")
                    follow_ups.append("Are you looking for physical books or e-books?")
                    if not entities.get("budget"):
                        follow_ups.append("What is your budget for the book?")
                elif "dress" in topic or "clothing" in topic:
                    follow_ups.append("What's the occasion for the dress (e.g., casual, formal)?")
                    follow_ups.append("Do you have a preferred style or color?")
                    if not entities.get("budget"):
                        follow_ups.append("What is your budget for the dress?")
                else:
                    # Dynamic follow-up questions using LLM
                    prompt = f"""
                    Generate 2-3 relevant follow-up questions for the following user input and topic, tailored to the context.
                    Input: {state['user_input']}
                    Topic: {topic or 'unknown'}
                    Output format: ```json
                    ["question 1", "question 2", "question 3"]
                    ```
                    """
                    try:
                        response = self.llm_service.generate_response(prompt)
                        dynamic_questions = json.loads(response.strip("```json\n").strip("```"))
                        follow_ups.extend(dynamic_questions[:3])  # Limit to 3 questions
                    except (json.JSONDecodeError, ValueError):
                        follow_ups.append("Could you provide more details about your request?")
                if not entities.get("location"):
                    follow_ups.append("Do you need information for a specific region or state?")
            intent["follow_up_questions"] = follow_ups
        return state

    def _handle_non_standard(self, state: State) -> State:
        web_results = []
        for intent in state["intents"]:
            if intent["category"] == "other":
                query = state["user_input"]
                if isinstance(query, str):
                    web_results = self.search_service.search_web(query)
        return {**state, "web_search_results": web_results}

    def process_input(self, user_input: str) -> List[Dict]:
        # Validate input
        if not user_input or user_input.isspace():
            return [{"error": "Please provide a valid input."}]
        if not isinstance(user_input, str):
            return [{"error": "Invalid input type. Please provide a text input."}]
        if self._is_offensive(user_input):
            return [{"error": "I'm sorry, but I can't assist with that request. Please provide a different query."}]
        state = self.graph.invoke({
            "user_input": user_input,
            "intents": [],
            "web_search_results": []
        })
        return [
            {
                "intent_category": intent["category"],
                "key_entities": intent["key_entities"],
                "confidence_score": intent["confidence"],
                "follow_up_questions": intent["follow_up_questions"],
                "web_search_results": state["web_search_results"] if intent["category"] == "other" else [],
                "validation_errors": intent.get("validation_errors", []),
                "conflict": intent.get("conflict", "")
            } for intent in state["intents"]
        ]
