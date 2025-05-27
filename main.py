from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, register, db_class  # import all routers here

app = FastAPI()

# Setup CORS for Flutter (allow all origins for dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(register.router)
app.include_router(db_class.router)  # ensure this is imported and included

@app.get("/")
def read_root():
    return {"message": "FastAPI is working!"}

# Optional: print all registered routes on startup for debugging
@app.on_event("startup")
def print_routes():
    print("Registered routes:")
    for route in app.routes:
        print(route.path)
