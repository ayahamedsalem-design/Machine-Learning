from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from postgresdb import engine, get_db
import user_table

# Automatically create tables in the database if they do not exist
user_table.Base.metadata.create_all(bind=engine)

app = FastAPI()

from pydantic import BaseModel

# The data model coming from the request
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

@app.post("/users/")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    # Check if the username or email already exists (optional)
    existing_user = db.query(user_table.User).filter(user_table.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Storing the password (ideally, it should be hashed, but for this example, we will include it as is for now)
    new_user = user_table.User(
        username=user.username,
        email=user.email,
        password_hash=user.password  # It should be hashed using, for example, bcrypt.
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "User created successfully in PostgreSQL!", "user": {
        "id": new_user.id,
        "username": new_user.username,
        "email": new_user.email
    }}