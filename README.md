clone beatcode-server
cd beatcode-server

python -m venv venv
venv/Scripts/Activate

python -m pip install -r requirements.txt

make .env using .env.example

cd app

python -m db.init --d
pytest tests/

fastapi dev main.py
uvicorn main:app

http://127.0.0.1:8000/docs