# AI Personal Assistant Bot

## Description
This project implements an intelligent personal assistant bot that processes natural language user inputs and converts them into structured data. The bot can handle various types of requests including dining reservations, travel bookings, cab services, and gift suggestions.

## Features
- Natural language processing of user inputs
- Intent classification (dining, travel, gifting, cab_booking)
- Entity extraction (dates, locations, preferences, etc.)
- Follow-up questions generation
- Web search integration for non-standard queries


## Project Structure
```
AI Personal Assistant Bot/
├── frontend/
│   ├── app.py          
│   ├── styles.css      
│   └── __init__.py
├── utils/
│   ├── intent_parser.py    
│   └── __init__.py
├── services/
│   ├── llm_service.py      
│   ├── search_service.py   
│   └── __init__.py
└── config/
    ├── settings.py         
    └── __init__.py
```

## Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment (recommended)

## Setup Instructions

1. Clone the repository:
   ```bash
   git clone https://github.com/Karthikaaaaaa/Personal-Assistant-Bot-.git
   cd Personal-Assistant-Bot
   ```

2. Create and activate a virtual environment:
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate
   ```

   ```bash
   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   - Create a `.env` file in the root directory
   - Add necessary API keys and configuration settings

5. Run the application:
   ```bash
   # From the frontend directory
   python app.py
   ```

## Usage Examples

1. Dining Reservation:
   ```
   "Need a sunset-view table for two tonight; gluten-free menu a must"
   ```

2. Travel Booking:
   ```
   "Book a flight to Paris for next week, budget around $1000"
   ```

3. Cab Booking:
   ```
   "Need a cab from airport to downtown tomorrow at 3 PM"
   ```

4. Gift Suggestions:
   ```
   "Suggest a birthday gift for my wife, budget $200"
   ```

## API Endpoints

- `POST /process_input`: Process user input and return structured data
  - Request body: `{"user_input": "your query here"}`
  - Response: JSON containing intents, entities, and follow-up questions

I have attached a pdf for reference, it has inputs and outputs of a case where in multiple intents are present.



