import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from typing import Annotated
from fastapi import FastAPI, Depends, Query, HTTPException
from sqlmodel import Field, Session, SQLModel, create_engine, select

load_dotenv()

class HeroBase(SQLModel):
    name: str = Field(index=True)
    age: int | None = Field(default=None, index=True)

class Hero(HeroBase, table=True):
    id: int = Field(default=None, primary_key=True)
    secret_name: str

class HeroPublic(HeroBase):
    id:int

class HeroCreate(HeroBase):
    secret_name: str

class HeroUpdate(HeroBase):
    name: str | None = None
    age: int | None = None
    secret_name: str | None = None

database_url = os.getenv("DATABASE_URL")
print(f"database_url: {database_url}")

engine = create_engine(database_url, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/heroes", response_model=HeroPublic)
def create_hero(hero: HeroCreate, session: SessionDep):
    db_hero = Hero.model_validate(hero)
    session.add(db_hero)
    session.commit()
    session.refresh(db_hero)
    return db_hero

@app.get("/heroes", response_model=list[HeroPublic])
def read_heroes(
        session: SessionDep,
        offset: int = 0,
        limit: Annotated[int, Query(le=100)] = 100
):
    heroes = session.exec(select(Hero).offset(offset).limit(limit)).all()
    return heroes

@app.get("/heroes/{hero_id}", response_model=HeroPublic)
def read_hero(hero_id: int, session: SessionDep):
    hero = session.get(Hero, hero_id)
    if not hero:
        raise HTTPException(status_code=404, detail="Hero not found")
    return hero

@app.patch("/heroes/{hero_id}", response_model=HeroPublic)
def update_hero(hero_id: int, hero: HeroUpdate, session: SessionDep):
    hero_db = session.get(Hero, hero_id)
    if not hero_db:
        raise HTTPException(status_code=404, detail="Hero not found")
    hero_data = hero.model_dump(exclude_unset=True)
    hero_db.sqlmodel_update(hero_data)
    session.add(hero_db)
    session.commit()
    session.refresh(hero_db)
    return hero_db

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