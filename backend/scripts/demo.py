import os
import sys
import json

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

def run_demo():
    client = TestClient(app)

    print("\n" + "=" * 60)
    print(" VISIONTRACE AI - BACKEND PERSON 2 DEMONSTRATION")
    print("=" * 60 + "\n")

    print("[*] Checking Health Endpoint (/api/v1/health):")
    health = client.get("/api/v1/health").json()
    print(json.dumps(health, indent=2))
    print()

    queries = [
        "Find the red car",
        "Find the person wearing blue",
        "Where was the red car first seen?",
        "Track the red car across all cameras",
        "Did the red car enter the campus?",
        "Show evidence of the red car at the main gate",
        "Find a vehicle that does not exist",
    ]

    for idx, q in enumerate(queries, start=1):
        print("-" * 60)
        print(f"TEST QUERY #{idx}: \"{q}\"")
        resp = client.post("/api/v1/query", json={"query": q})
        data = resp.json()
        print(f"Response Status : {resp.status_code}")
        print(f"Grounded Answer : {data['answer']}")
        print(f"Matches Found   : {len(data['matches'])}")
        for m in data['matches']:
            print(f"  • {m['camera_id']} ({m['camera_name']}) @ {m['timestamp']}s [conf: {m['confidence']}] - {m['description']}")
            if m.get('evidence_url'):
                print(f"    Evidence URL: {m['evidence_url']}")
        if data.get('trajectory'):
            print(f"Trajectory ({len(data['trajectory'])} nodes):")
            for pt in data['trajectory']:
                print(f"    -> {pt['camera_id']} ({pt['camera_name']}) @ {pt['timestamp']}s [{pt.get('location', '')}]")
        print()

    print("-" * 60)
    print("TEST TRAJECTORY API (POST /api/v1/trajectory):")
    traj_req = {"object_type": "car", "color": "red"}
    t_resp = client.post("/api/v1/trajectory", json=traj_req).json()
    print(json.dumps(t_resp, indent=2))
    print("\n" + "=" * 60)
    print(" DEMO COMPLETED SUCCESSFULLY")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    run_demo()
