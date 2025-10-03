from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field, computed_field
from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated, Literal
from fastapi.responses import JSONResponse
import json
import psycopg2
import os

# ✅ Load database URL from environment variable (Render -> Environment tab)
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Database Connection ----------------
def get_db_connection():
    try:
        conn = psycopg2.connect("postgresql://nakul:l5ud6TnGWxJLFd21B4yDyuFQvV3a60rM@dpg-d3ft8n2dbo4c73e8l6b0-a/bankx_yy3p")
        conn.autocommit = True
        return conn
    except Exception as e:
        print("❌ PostgreSQL Connection Error:", e)
        return None

# ---------------- JSON File Helpers (optional) ----------------
def load_user():
    try:
        with open("details.json","r") as f:
            users=json.load(f)
            return users
    except FileNotFoundError:
        return []

def save_user(users):
    with open("details.json","w") as f:
        json.dump(users,f,indent=4)

def generate_user_id(users):
    if users:
        return max(user["id"] for user in users) + 1
    return 1

# ---------------- Root Endpoint ----------------
@app.get("/")
def read_root():
    return {"message": "This is my BankX API (PostgreSQL version)"}

# ---------------- Models ----------------
class CreateUser(BaseModel):
    name:str
    email:EmailStr
    account_type:str
    deposit:float

    @computed_field
    @property
    def new_balance(self)->float:
        return self.deposit

class User(BaseModel):
    id:int
    name:Annotated[str, Field(..., description="Full Name of the User", min_length=3)]
    email:Annotated[EmailStr, Field(..., description="Email of the User")]
    account_type:Annotated[Literal["Saving","Current","Business"], Field(..., description="Type of Account")]
    balance:Annotated[float, Field(..., description="Balance in the Account", ge=0)]

# ---------------- API ----------------
@app.post("/createUser", response_model=User)
def create_user(user: CreateUser):
    users = load_user()

    if any(u["email"] == user.email for u in users):
        raise HTTPException(status_code=400, detail="Email already exists")

    new_id = generate_user_id(users)
    new_user = User(
        id=new_id,
        name=user.name,
        email=user.email,
        account_type=user.account_type,
        balance=user.new_balance
    )

    users.append(new_user.model_dump())
    save_user(users)

    # ✅ Save to PostgreSQL
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100),
                    email VARCHAR(100) UNIQUE,
                    account_type VARCHAR(50),
                    balance FLOAT
                )
            """)

            cursor.execute("""
                INSERT INTO users (id, name, email, account_type, balance)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (email) DO NOTHING
            """, (new_user.id, new_user.name, new_user.email, new_user.account_type, new_user.balance))

            conn.commit()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PostgreSQL Error: {e}")
        finally:
            cursor.close()
            conn.close()

    return new_user
