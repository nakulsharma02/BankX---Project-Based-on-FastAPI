from fastapi import FastAPI,HTTPException
from pydantic import BaseModel,EmailStr,Field,computed_field
from fastapi.middleware.cors import CORSMiddleware;
from typing import Annotated,Literal
from fastapi.responses import JSONResponse
import json
import mysql.connector
from mysql.connector import Error

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",       # your MySQL user
            password="nakul",   # your MySQL password
            database="BankX"
        )
        conn.autocommit = True
        return conn
    except Error as e:
        print("❌ MySQL Connection Error:", e)
        return None
def load_user():
    try:
        with open("details.json","r") as f:
            users=json.load(f)
            return users
    except FileNotFoundError:
        raise FileNotFoundError("User data file not found.")
def save_user(users):
    with open("details.json","w") as f:
        json.dump(users,f,indent=4)
def generate_user_id(users):
    if users:
        return max(user["id"] for user in users) + 1
    return 1
id_user = generate_user_id(load_user())
@app.get("/")
def read_root():
    return {"This is my BankX API"}
new_balance=0.0
class CreateUser(BaseModel):
    name:str
    email:EmailStr
    account_type:str
    deposit:float
    @computed_field
    @property
    def new_balance(self)->float:
        return  self.deposit
class User(BaseModel):
    id:int
    name:Annotated[str,Field(...,description="Full Name of the User",min_length=3)]
    email:Annotated[EmailStr,Field(...,description="Email of the User")]
    account_type:Annotated[Literal["Saving","Current","Business"],Field(...,description="Type of Account")]   
    balance:Annotated[float,Field(...,description="Balance in the Account",ge=0)]
@app.post("/createUser",response_model=User)
def create_user(user:CreateUser):
    users=load_user()
    if any(u["email"]==user.email for u in users):
        raise HTTPException(status_code=400,detail="Email already exists")
    new_id = generate_user_id(users)
    new_user=User(
        id=new_id,
        name=user.name,
        email=user.email,
        account_type=user.account_type,
        balance=user.new_balance
    )
    users.append(new_user.model_dump())
    save_user(users)
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (id, name, email, account_type, balance)
                VALUES (%s, %s, %s, %s, %s)
            """, (new_user.id, new_user.name, new_user.email, new_user.account_type, new_user.balance))
            conn.commit()
        except Error as e:
            raise HTTPException(status_code=500, detail=f"MySQL Error: {e}")
        finally:
            cursor.close()
            conn.close()

    return new_user
    