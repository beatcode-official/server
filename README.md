# BeatCode Server

## Quick Introduction
BeatCode is a platform providing head-to-head coding battles.

This README.md provides information on how to install and run the server.

For information on how to integrate with the frontend, check out DOCS.md.

**[More comprehensive documentation](https://deepwiki.com/beatcode-official/server)**

## Requirements
1. Python (this repo uses Python 3.11)
2. Ready-to-go PostgreSQL database
3. Running Docker Engine

## Installation

Step 1: Clone this repo

```bash
git clone https://github.com/beatcode-official/server.git
cd server
```

Step 2: [OPTIONAL] Create a new Python virtual environment
```bash
python -m venv venv
venv/Scripts/Activate # For Windows
source venv/bin/activate # For Linux
```

Step 3: Install the required Python dependencies
```bash
python -m pip install -r requirements.txt
```

Step 4: Copy the .env.example to a new file and name it .env (place in the same folder). This environment file will store variables used by the server. Variables you'll likely need to change to match your system settings are:

```
1. DB_USER, DB_PASSWORD, DB_HOST
2. TEST_DB_USER, TEST_DB_PASSWORD, TEST_DB_HOST
3. RESEND_API_KEY (leave as default if you don't possess one)
4. FRONTEND_URL
5. SECRET_KEY
6. OPENAI_API_KEY (leave as default if you don't possess one)
```

Step 5: Initialize the database
```bash
cd app
python -m db.init --dropall
```

Step 6: Start the server
```bash
uvicorn main:app # For normal running
fastapi dev main.py # For development (auto reload)
```

## Testing
### Unit Tests
These are pytest scripts I wrote to test the individual components of the backend. To run them:
```bash
pytest tests/unit # Test all components
pytest tests/unit/code_execution_test.py # Test a single component
pytest tests/unit/problem_test.py # Test a single component
```

### Integration Tests
These are user-simulation scripts I wrote to test the endpoints as a whole and serves as a good enough sanity check when updating your code. Feel free to modify it however you like. Note that to run these the server must be running on `TESTING=True` in your .env file.

To run these tests, run them as normal Python scripts from the `/app` directory:
```bash
python tests/integration/auth_test.py # Test authentication endpoints
python tests/integration/game_test.py # Test game endpoints
python tests/integration/room_test.py # Test room endpoints
python tests/integration/practice_test.py # Test practice mode
```