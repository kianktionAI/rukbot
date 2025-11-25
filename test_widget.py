from fastapi.testclient import TestClient
from rukbot import app

client = TestClient(app)

def run_test():
    response = client.get("/widget")
    print("\nSTATUS:", response.status_code)
    print("BODY:\n", response.text)

# Explicitly call it
run_test()
