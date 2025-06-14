from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
from routes import auth, register, db_class, db_student, db_exam, db_question, db_scheme, db_result, db_homepage, db_scan, db_submission, db_analytics, db_profile, db_password  # your routers

app = FastAPI()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # adjust in production
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

app.include_router(auth.router)
app.include_router(register.router)
app.include_router(db_class.router)
app.include_router(db_student.router)
app.include_router(db_exam.router)
app.include_router(db_question.router)
app.include_router(db_scheme.router)
app.include_router(db_result.router)
app.include_router(db_homepage.router)
app.include_router(db_scan.router)
app.include_router(db_submission.router)
app.include_router(db_analytics.router)
app.include_router(db_profile.router)
app.include_router(db_password.router)

@app.get("/")
def read_root():
    return {"message": "FastAPI is working!"}

@app.on_event("startup")
def print_routes():
    print("Registered routes:")
    for route in app.routes:
        print(route.path)


