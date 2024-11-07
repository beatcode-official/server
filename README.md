clone beatcode-server
cd beatcode-server

python -m venv venv
venv/Scripts/Activate

python -m pip install -r requirements.txt

make .env using .env.example

cd app

python -m db.init --d
python .\tests\integration\user_simulator.py
pytest tests/unit

fastapi dev main.py
uvicorn main:app

http://127.0.0.1:8000/docs
