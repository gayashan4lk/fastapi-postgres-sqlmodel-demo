import os
from dotenv import load_dotenv
from typing import Annotated
from fastapi import FastAPI, Depends, Query, HTTPException
from sqlmodel import Field, Session, SQLModel, create_engine, select

load_dotenv()

class Hero(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    age: int | None = Field(default=None, index=True)
    secret_name: str

database_url = os.getenv("DATABASE_URL")
print(f"database_url: {database_url}")

engine = create_engine(database_url, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]

app = FastAPI()

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.post("/heroes")
def create_hero(hero: Hero, session: SessionDep):
    session.add(hero)
    session.commit()
    session.refresh(hero)
    return hero

@app.get("/heroes")
def read_heroes(session: SessionDep, offset: int = 0, limit: Annotated[int, Query(le=100)] = 100) -> list[Hero]:
    heroes = session.exec(select(Hero).offset(offset).limit(limit)).all()
    return heroes

@app.get("/heroes/{hero_id}")
def read_hero(hero_id: int, session: SessionDep):
    hero = session.get(Hero, hero_id)
    if not hero:
        raise HTTPException(status_code=404, detail="Hero not found")
    return hero

@app.delete("/heroes/{hero_id}")
def delete_hero(hero_id:int, session: SessionDep):
    hero = session.get(Hero, hero_id)
    if not hero:
        raise HTTPException(status_code=404, detail="Hero not found")
    session.delete(hero)
    session.commit()
    return {"ok": True}


@app.get("/")
async def root():
    return {"message": f"database_url: {database_url}"}