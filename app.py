from typing import Dict, Any
import os
import datetime
import os.path
from fastapi import HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
import jwt
import sqlite3
from fastapi import FastAPI
from fastapi.responses import FileResponse
import uvicorn
from starlette.responses import Response
import base64

app = FastAPI()

JWT_SECRET_KEY = "secret"
JWT_ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

conn = sqlite3.connect('example.db')
conn.execute('PRAGMA foreign_keys = ON')
c = conn.cursor()

c.execute('''
          CREATE TABLE IF NOT EXISTS users (
          username TEXT PRIMARY KEY,
          password TEXT,
          phone TEXT,
          car_id INTEGER,
          FOREIGN KEY (car_id) REFERENCES cars(car_id)
          )
          ''')

c.execute('''
          CREATE TABLE IF NOT EXISTS cars (
          car_id INTEGER PRIMARY KEY,
          car_name TEXT,
          model TEXT ,
          firmware_logs TEXT
          )
          ''')

c.execute('''
          CREATE TABLE IF NOT EXISTS ecus (
          ecu_id INTEGER PRIMARY KEY,
          ecu_name TEXT
          )
          ''')

c.execute('''
          CREATE TABLE IF NOT EXISTS firmware (
          firmware_id INTEGER PRIMARY KEY,
          car_id INTEGER,
          ecu_id INTEGER,
          firmware_version TEXT,
          description TEXT,
          FOREIGN KEY (car_id) REFERENCES cars(car_id),
          FOREIGN KEY (ecu_id) REFERENCES ecus(ecu_id)
          )
          ''')
c.execute('''
          CREATE TABLE IF NOT EXISTS update_logs (
          log_id INTEGER PRIMARY KEY,
          car_id INTEGER,
          firmware_logs TEXT,
          FOREIGN KEY (car_id) REFERENCES cars(car_id)
          )
          ''')


c.execute("INSERT OR IGNORE INTO cars (car_id, car_name, model, firmware_logs) VALUES (1, 'Toyota Camry', '2022', '100%')")
c.execute(
    "INSERT OR IGNORE INTO ecus (ecu_id, ecu_name) VALUES (1, 'Engine Control Unit')")
c.execute(
    "INSERT OR IGNORE INTO firmware (firmware_id, car_id, ecu_id, firmware_version, description) VALUES (1, 1, 1, '1.0', 'Initial release')")
c.execute("INSERT OR IGNORE INTO users (username, password, phone, car_id) VALUES ('user1', ?, '123-456-7890', 1)",
          (pwd_context.hash("password"),))
conn.commit()

conn.close()


def get_user(username: str) -> Dict[str, Any]:
    conn = sqlite3.connect('example.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()
    if user is None:
        return None
    return {"username": user[0], "password": user[1], "phone": user[2], "car_id": user[3]}


def authenticate_user(username: str, password: str) -> Dict[str, Any]:
    user = get_user(username)
    if not user:
        return None
    if not pwd_context.verify(password, user["password"]):
        return None
    return user


def create_jwt_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=3000),
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


@app.post("/signup/")
async def signup(request: Request):
    userData = await request.json()
    print(userData)
    conn = sqlite3.connect('example.db')
    c = conn.cursor()
    try:
        hashed_password = pwd_context.hash(str(userData['password']))
        c.execute("INSERT INTO users (username, password, phone, car_id) VALUES (?, ?, ?, ?)",
                  (userData['username'], hashed_password, str(userData['phone']), userData['car_id']))
        conn.commit()
        return {"message": "User registered successfully"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Username already exists")
    finally:
        conn.close()


@app.post("/token/")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    currentDate = datetime.datetime.now()
    date = currentDate.strftime("%d-%m-%Y")
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_jwt_token(user["username"])
    return {"access_token": token, "token_type": "bearer", "date": date}


@app.get("/user")
async def read_users_me(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=401, detail="Invalid authentication credentials")
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=401, detail="Invalid authentication credentials")

    user = get_user(username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/cars/")
async def read_car(car_id: int, token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        print(payload)
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=401, detail="Invalid authentication credentials")
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=401, detail="Invalid authentication credentials")

    conn = sqlite3.connect('example.db')
    c = conn.cursor()
    c.execute("SELECT * FROM cars WHERE car_id=?", (car_id,))
    car = c.fetchone()
    conn.close()
    if car is None:
        raise HTTPException(status_code=404, detail="Car not found")
    return {"car_id": car[0], "car_name": car[1], "model": car[2]}


@app.get("/ecus/{ecu_id}")
async def read_ecu(ecu_id: int):
    conn = sqlite3.connect('example.db')
    c = conn.cursor()
    c.execute("SELECT * FROM ecus WHERE ecu_id=?", (ecu_id,))
    ecu = c.fetchone()
    conn.close()
    if ecu is None:
        raise HTTPException(status_code=404, detail="ECU not found")
    return {"ecu_id": ecu[0], "ecu_name": ecu[1]}


@app.get("/firmware/")
async def get_firmware(car_id: int, ecu_id: int, token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=401, detail="Invalid authentication credentials")
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=401, detail="Invalid authentication credentials")
    conn = sqlite3.connect('example.db')
    c = conn.cursor()
    c.execute("SELECT * FROM firmware WHERE car_id=? AND ecu_id=? AND firmware_id = (SELECT MAX(firmware_id) FROM "
              "firmware WHERE car_id=? AND ecu_id=?)", (car_id, ecu_id, car_id, ecu_id))
    firmware = c.fetchone()
    conn.close()
    if firmware is None:
        raise HTTPException(status_code=404, detail="Firmware not found")
    base64_description = base64.b64encode(firmware[4].encode()).decode()
    return {
        "firmware_version": firmware[3],
        "firmware_id": firmware[0],
        "description": base64_description
    }


@app.post("/send_firmware/")
async def receive_firmware(request: Request):
    json = await request.json()

    # Access the firmware data using the `firmware_data` parameter
    car_id = json['car_id']
    ecu_id = json['ecu_id']
    firmware_version = json['firmware_version']
    description = json['description']

    # Check if the car_id and ecu_id exist in their respective tables
    conn = sqlite3.connect('example.db')
    c = conn.cursor()
    c.execute("SELECT car_id FROM cars WHERE car_id=?", (car_id,))
    car_exists = c.fetchone()[0]
    c.execute("SELECT ecu_id FROM ecus WHERE ecu_id=?", (ecu_id,))
    ecu_exists = c.fetchone()[0]
    print("car_exists:", car_exists)
    print("ecu_exists:", ecu_exists)
    if car_exists and ecu_exists:
        # Insert the firmware data into the database
        c.execute("INSERT OR IGNORE INTO firmware (car_id, ecu_id, firmware_version, description) "
                  "VALUES (?, ?, ?, ?)",
                  (car_id, ecu_id, firmware_version, description))
        conn.commit()

        # Get the firmware_id of the inserted data
        c.execute(
            "SELECT firmware_id FROM firmware WHERE car_id=? AND ecu_id=? AND firmware_id = (SELECT MAX(firmware_id) FROM "
            "firmware)", (car_id, ecu_id))
        firmware_id = c.fetchone()

        # Access the file using the `file` parameter
        contents = json['file']
        with open(f"firmwares/{firmware_id[0]}.fota", "w") as f:
            f.write(contents)

        conn.close()
        return {"message": "Firmware data and file received",
                "firmware_id":firmware_id[0]}
    else:
        conn.close()
        return Response(status_code=400, content="Invalid car_id or ecu_id")


@app.get("/download/")
async def download_file(filename: str, token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=401, detail="Invalid authentication credentials")
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=401, detail="Invalid authentication credentials")
    file_path = f"firmwares/{filename}"
    return FileResponse(file_path, headers={"Content-Disposition": f"attachment; filename={filename}"})


@app.post("/ecu_diag/")
async def save_json_data(car_id: int, ecu_id: int, request: Request):

    json_data = await request.json()

    now = datetime.datetime.now()
    date_time = now.strftime("Date-%d-%m-%Y, Time-%H-%M-%S")
    file_name = f"{car_id}-{ecu_id}-({date_time}).diag"

    file_path = f'{os.getcwd()}/Diagnostics/{file_name}'

    if os.path.exists(file_path):
        with open(file_path, "a") as f:
            f.write('\n' + json_data['file'])
        return {"message": "data appended successfully"}
    else:
        with open(file_path, "w") as f:
            f.write(base64.b64decode(json_data['file'].encode()).decode())
            f.close()
        return {"message": "data created successfully"}


@app.post("/update_logs/")
async def add_car_logs(car_id: int, request: Request):
    json_data = await request.json()

    # Access the car logs data from the JSON

    logs = json_data['logs']

    # Add the car logs to the database
    conn = sqlite3.connect('example.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO update_logs (car_id, firmware_logs) VALUES (?, ?) ", (car_id, logs))
    conn.commit()
    conn.close()

    return {"message": "Update logs is stored successfully"}


if __name__ == '__main__':
    uvicorn.run("app:app", port=80, reload=True, access_log=True)
