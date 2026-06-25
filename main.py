from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from typing import List, Annotated
from auth import create_access_token
import models
from database import engine, SessionLocal
from sqlalchemy.orm import Session
from jose import  JWTError, jwt
from settings import SECRET_KEY, ALGORITHM, FRONTEND_ORIGIN

from security import hash_password, verify_password
from fastapi.security import OAuth2PasswordBearer
from schemas import UserCreate, WorkoutCreate, WorkoutResponse
from fastapi.middleware.cors import CORSMiddleware



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],  # e.g. http://localhost:3000
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
models.Base.metadata.create_all(bind=engine)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]





def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: db_dependency):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")

        if email is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.email == email).first()

    if user is None:
        raise credentials_exception

    return user



@app.get("/me")
def get_me(current_user: models.User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
    }

@app.post("/workouts", response_model=WorkoutResponse)
def create_workouts(workout: WorkoutCreate, db: db_dependency, current_user: models.User = Depends(get_current_user)):
    db_workout = models.Workout(
        date=workout.date,
        user_id= current_user.id
    )

    for ex in workout.exercises:
        db_ex = models.Exercise(
            name=ex.name
        )

        for item in ex.sets:
            db_set = models.ExerciseSet(
                reps=item.reps,
                weight=item.weight
            )
            db_ex.sets.append(db_set)

        db_workout.exercises.append(db_ex)

    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)

    return db_workout

@app.post("/users")
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")


    pw = payload.password.strip()
    if len(pw.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=400,
            detail="Password too long (bcrypt supports max 72 bytes).",
        )
    user = models.User(
            name=payload.name,
            email=payload.email,
            password=hash_password(pw),
        )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"id": user.id, "name": user.name, "email": user.email}

@app.get("/workouts", response_model=List[WorkoutResponse])
def get_workouts(db: db_dependency, current_user: models.User = Depends(get_current_user)):
 workouts = (
        db.query(models.Workout)
        .filter(models.Workout.user_id == current_user.id)
        .all()
    )  
 return workouts

@app.get("/workouts/{workout_id}", response_model=WorkoutResponse)
def get_workout(workout_id: int, db: db_dependency , current_user: models.User = Depends(get_current_user)):
    workout = (
        db.query(models.Workout)
        .filter(models.Workout.id == workout_id, models.Workout.user_id == current_user.id)
        .first()
    )

    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    return workout

@app.delete("/workouts/{workout_id}", response_model=WorkoutResponse)
def delete_workout(workout_id: int, db: db_dependency , current_user: models.User = Depends(get_current_user)):
    workout = (
        db.query(models.Workout)
        .filter(models.Workout.id == workout_id, models.Workout.user_id == current_user.id)        
        .first()
    )

    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    db.delete(workout)
    db.commit()

    return workout

@app.put("/workouts/{workout_id}", response_model=WorkoutResponse)
def update_workout(workout_id: int, workout: WorkoutCreate, db: db_dependency, current_user: models.User = Depends(get_current_user)):
    db_workout = (
        db.query(models.Workout)
            .filter(models.Workout.id == workout_id, models.Workout.user_id == current_user.id) 
            .first()
    )

    if not db_workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    db_workout.date = workout.date
    db_workout.exercises.clear()


    for ex in workout.exercises:
        db_ex = models.Exercise(
            name=ex.name,
            workout_id=db_workout.id
        )

        for item in ex.sets:
            db_set = models.ExerciseSet(
                reps=item.reps,
                weight=item.weight
            )
            db_ex.sets.append(db_set)

        db.add(db_ex)

    db.commit()
    db.refresh(db_workout)

    return db_workout


@app.post("/login")
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency):
    user = (
        db.query(models.User)
        .filter(models.User.email == form_data.username)
        .first()
    )

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": user.email})

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }