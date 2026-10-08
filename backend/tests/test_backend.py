import sys
import os
import pytest

# Ensure backend folder is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base, get_db
from app.models.event import Camera, Event
from app.services.query_service import query_service
from app.services.retrieval_service import retrieval_service
from app.services.trajectory_service import trajectory_service
from app.schemas.query import QueryRequest, TrajectoryRequest
from app.main import app

from sqlalchemy.pool import StaticPool

# In-memory SQLite for testing with StaticPool so all connections share the same memory DB
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()

    # Populate test cameras
    cams = [
        Camera(camera_id="CAM-01", camera_name="Main Gate", location="Main Gate", status="online"),
        Camera(camera_id="CAM-02", camera_name="Parking", location="Parking", status="online"),
        Camera(camera_id="CAM-03", camera_name="Building Entrance", location="Building", status="online"),
        Camera(camera_id="CAM-04", camera_name="Exit Gate", location="Exit Gate", status="online"),
    ]
    for c in cams:
        db.add(c)

    # Populate test events
    events = [
        Event(
            event_id="evt_001",
            camera_id="CAM-01",
            camera_name="Main Gate",
            timestamp=12.4,
            confidence=0.94,
            event_type="vehicle_detected",
            object_type="car",
            color="red",
            action="enter",
            location="Main Gate",
            description="red car detected entering campus",
            evidence_url="/api/v1/evidence/evt_001",
        ),
        Event(
            event_id="evt_002",
            camera_id="CAM-02",
            camera_name="Parking",
            timestamp=18.7,
            confidence=0.88,
            event_type="vehicle_detected",
            object_type="car",
            color="red",
            action="park",
            location="Parking",
            description="red car detected in parking area",
            evidence_url="/api/v1/evidence/evt_002",
        ),
        Event(
            event_id="evt_003",
            camera_id="CAM-03",
            camera_name="Building Entrance",
            timestamp=15.1,
            confidence=0.92,
            event_type="person_detected",
            object_type="person",
            color="blue",
            action="walk",
            location="Building",
            description="person wearing blue shirt entered main lobby",
            evidence_url="/api/v1/evidence/evt_003",
        ),
        Event(
            event_id="evt_004",
            camera_id="CAM-04",
            camera_name="Exit Gate",
            timestamp=25.2,
            confidence=0.91,
            event_type="vehicle_detected",
            object_type="car",
            color="red",
            action="exit",
            location="Exit Gate",
            description="red car exiting through gate",
            evidence_url="/api/v1/evidence/evt_004",
        ),
        Event(
            event_id="evt_005",
            camera_id="CAM-01",
            camera_name="Main Gate",
            timestamp=8.0,
            confidence=0.89,
            event_type="vehicle_detected",
            object_type="truck",
            color="white",
            action="enter",
            location="Main Gate",
            description="white delivery truck entered main gate",
            evidence_url="/api/v1/evidence/evt_005",
        ),
    ]
    for ev in events:
        db.add(ev)

    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def client():
    return TestClient(app)

def test_query_parser_rules():
    """Verify deterministic parser extraction for core test queries."""
    p1 = query_service.parse_query("Find the red car")
    assert p1.object_type == "car"
    assert p1.color == "red"
    assert p1.operation == "search"

    p2 = query_service.parse_query("Find the person wearing blue")
    assert p2.object_type == "person"
    assert p2.color == "blue"

    p3 = query_service.parse_query("Where was the red car first seen?")
    assert p3.object_type == "car"
    assert p3.color == "red"
    assert p3.operation == "first_seen"

    p4 = query_service.parse_query("Track the red car across all cameras")
    assert p4.object_type == "car"
    assert p4.color == "red"
    assert p4.operation == "trajectory"

    p5 = query_service.parse_query("Did the red car enter the campus?")
    assert p5.object_type == "car"
    assert p5.color == "red"
    assert p5.action == "enter"

    p6 = query_service.parse_query("Show evidence of the red car at the main gate")
    assert p6.object_type == "car"
    assert p6.color == "red"
    assert p6.location == "main gate"

    p7 = query_service.parse_query("Find a vehicle that does not exist")
    assert p7.object_type == "car" # vehicle maps to car/vehicle synonym

def test_api_query_1_find_red_car(client):
    """Test query: 'Find the red car'"""
    res = client.post("/api/v1/query", json={"query": "Find the red car"})
    assert res.status_code == 200
    data = res.json()
    assert data["query"] == "Find the red car"
    assert len(data["matches"]) >= 1
    # Check match structure
    m = data["matches"][0]
    assert m["camera_id"] in ["CAM-01", "CAM-02", "CAM-04"]
    assert "evidence_url" in m
    assert "red" in m["description"] or "car" in m["description"]
    assert len(data["answer"]) > 0

def test_api_query_2_find_person_blue(client):
    """Test query: 'Find the person wearing blue'"""
    res = client.post("/api/v1/query", json={"query": "Find the person wearing blue"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["matches"]) == 1
    assert data["matches"][0]["camera_id"] == "CAM-03"
    assert data["matches"][0]["event_type"] == "person_detected"
    assert "blue" in data["matches"][0]["description"]

def test_api_query_3_first_seen(client):
    """Test query: 'Where was the red car first seen?'"""
    res = client.post("/api/v1/query", json={"query": "Where was the red car first seen?"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["matches"]) >= 1
    # Earliest timestamp for red car is 12.4s at CAM-01
    assert data["matches"][0]["camera_id"] == "CAM-01"
    assert data["matches"][0]["timestamp"] == 12.4
    assert "first seen" in data["answer"].lower() or "main gate" in data["answer"].lower()

def test_api_query_4_track_red_car(client):
    """Test query: 'Track the red car across all cameras'"""
    res = client.post("/api/v1/query", json={"query": "Track the red car across all cameras"})
    assert res.status_code == 200
    data = res.json()
    assert data["trajectory"] is not None
    assert len(data["trajectory"]) >= 2
    # Verify trajectory sequence CAM-01 -> CAM-02 -> CAM-04
    cam_seq = [pt["camera_id"] for pt in data["trajectory"]]
    assert cam_seq == ["CAM-01", "CAM-02", "CAM-04"]

def test_api_query_5_did_red_car_enter(client):
    """Test query: 'Did the red car enter the campus?'"""
    res = client.post("/api/v1/query", json={"query": "Did the red car enter the campus?"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["matches"]) >= 1
    # Top match should be the entrance at CAM-01
    assert data["matches"][0]["camera_id"] == "CAM-01"
    assert "entering" in data["matches"][0]["description"] or "enter" in data["matches"][0]["description"]

def test_api_query_6_show_evidence_main_gate(client):
    """Test query: 'Show evidence of the red car at the main gate'"""
    res = client.post("/api/v1/query", json={"query": "Show evidence of the red car at the main gate"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["matches"]) >= 1
    top = data["matches"][0]
    assert top["camera_id"] == "CAM-01"
    assert top["evidence_url"] == "/api/v1/evidence/evt_001"

def test_api_query_7_non_existent_event(client):
    """Test query: 'Find a purple helicopter' -> zero matches, grounded answer"""
    res = client.post("/api/v1/query", json={"query": "Find a purple helicopter"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["matches"]) == 0
    assert data["answer"] == "No matching event was found in the indexed footage."

def test_trajectory_api_post(client):
    """Test POST /api/v1/trajectory"""
    res = client.post("/api/v1/trajectory", json={"object_type": "car", "color": "red"})
    assert res.status_code == 200
    data = res.json()
    assert data["object_type"] == "car"
    assert data["color"] == "red"
    assert data["status"] == "consistent visual match"
    assert len(data["trajectory"]) == 3
    assert [p["camera_id"] for p in data["trajectory"]] == ["CAM-01", "CAM-02", "CAM-04"]
    assert len(data["links"]) == 2
    for link in data["links"]:
        assert link["transition_valid"] is True
        assert link["confidence"] > 0.7

def test_trajectory_api_get(client):
    """Test GET /api/v1/trajectory"""
    res = client.get("/api/v1/trajectory?object_type=car&color=red")
    assert res.status_code == 200
    data = res.json()
    assert len(data["trajectory"]) == 3
    assert data["trajectory"][0]["camera_id"] == "CAM-01"
    assert data["trajectory"][0]["timestamp"] == 12.4

def test_health_endpoint(client):
    """Test GET /api/v1/health"""
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "ollama" in data

def test_api_query_with_filters(client):
    """Test query with explicit camera_ids and time_range filters"""
    req = {
        "query": "Find the red car",
        "camera_ids": ["CAM-02"],
        "time_range": {"start": 15.0, "end": 20.0}
    }
    res = client.post("/api/v1/query", json=req)
    assert res.status_code == 200
    data = res.json()
    assert len(data["matches"]) == 1
    assert data["matches"][0]["camera_id"] == "CAM-02"
    assert data["matches"][0]["timestamp"] == 18.7

def test_api_query_last_seen(client):
    """Test last_seen operation: 'Where was the red car last seen?'"""
    res = client.post("/api/v1/query", json={"query": "Where was the red car last seen?"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["matches"]) >= 1
    # Latest timestamp for red car is 25.2s at CAM-04
    assert data["matches"][0]["camera_id"] == "CAM-04"
    assert data["matches"][0]["timestamp"] == 25.2
    assert "last seen" in data["answer"].lower() or "exit gate" in data["answer"].lower()

def test_trajectory_empty(client):
    """Test trajectory for non-existent vehicle"""
    res = client.post("/api/v1/trajectory", json={"object_type": "motorcycle", "color": "purple"})
    assert res.status_code == 200
    data = res.json()
    assert data["total_nodes"] == 0
    assert data["trajectory"] == []

def test_mock_ollama_grounded_answer(client, monkeypatch):
    """Test grounded answer generation when Ollama is available"""
    monkeypatch.setattr(query_service, "_check_ollama_health", lambda: True)

    def mock_ollama_call(query, matches):
        return "A red car was observed at the Main Gate at 12.4 seconds based on surveillance logs."

    monkeypatch.setattr(query_service, "_call_ollama_grounded", mock_ollama_call)

    res = client.post("/api/v1/query", json={"query": "Find the red car"})
    assert res.status_code == 200
    data = res.json()
    assert "surveillance logs" in data["answer"]

