import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool
from main import app, get_session

# Test database setup
@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session
    
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_root(client: TestClient):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"

def test_create_group(client: TestClient):
    """Test group creation"""
    response = client.post(
        "/group",
        json={"name": "Test Group", "mood": "chill", "budget_level": "low"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "code" in data
    assert "link" in data
    assert data["group"]["name"] == "Test Group"
    assert data["group"]["mood"] == "chill"

def test_join_group(client: TestClient):
    """Test joining a group"""
    # Create group first
    create_response = client.post(
        "/group",
        json={"name": "Test Group", "mood": "adventurous", "budget_level": "medium"}
    )
    code = create_response.json()["code"]
    
    # Join the group
    response = client.post(
        f"/group/{code}/join",
        json={"name": "Test User", "lat": 12.9716, "lng": 77.5946}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["member"]["name"] == "Test User"
    assert data["member"]["location_lat"] == 12.9716

def test_get_group(client: TestClient):
    """Test getting group details"""
    # Create and join
    create_response = client.post(
        "/group",
        json={"name": "Test Group", "mood": "foodie", "budget_level": "high"}
    )
    code = create_response.json()["code"]
    
    client.post(
        f"/group/{code}/join",
        json={"name": "User 1", "lat": 12.9716, "lng": 77.5946}
    )
    
    # Get group
    response = client.get(f"/group/{code}")
    assert response.status_code == 200
    data = response.json()
    assert data["group"]["name"] == "Test Group"
    assert len(data["members"]) == 1
    assert data["members"][0]["name"] == "User 1"

def test_create_poll(client: TestClient):
    """Test poll creation"""
    # Create group
    create_response = client.post(
        "/group",
        json={"name": "Test Group", "mood": "chill", "budget_level": "low"}
    )
    code = create_response.json()["code"]
    
    # Create poll
    response = client.post(
        f"/group/{code}/polls",
        json={
            "title": "Where to go?",
            "options": [
                {"id": "opt1", "title": "Cafe"},
                {"id": "opt2", "title": "Park"}
            ]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Where to go?"
    assert len(data["options"]["options"]) == 2

def test_vote_on_poll(client: TestClient):
    """Test voting on a poll"""
    # Setup: create group, join, create poll
    create_response = client.post(
        "/group",
        json={"name": "Test Group", "mood": "chill", "budget_level": "low"}
    )
    code = create_response.json()["code"]
    
    join_response = client.post(
        f"/group/{code}/join",
        json={"name": "Voter", "lat": 12.9716, "lng": 77.5946}
    )
    member_id = join_response.json()["member"]["id"]
    
    poll_response = client.post(
        f"/group/{code}/polls",
        json={
            "title": "Test Poll",
            "options": [{"id": "opt1", "title": "Option 1"}]
        }
    )
    poll_id = poll_response.json()["id"]
    
    # Vote
    response = client.post(
        f"/group/{code}/polls/{poll_id}/vote",
        json={"member_id": member_id, "option_id": "opt1", "emoji": "👍"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "opt1" in data["votes"]
    assert len(data["votes"]["opt1"]) == 1

def test_group_not_found(client: TestClient):
    """Test 404 for non-existent group"""
    response = client.get("/group/NOTEXIST")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_chat_with_planpal(client: TestClient):
    """Test chat with PlanPal mention"""
    # Create group
    create_response = client.post(
        "/group",
        json={"name": "Test Group", "mood": "chill", "budget_level": "low"}
    )
    code = create_response.json()["code"]
    
    # Join
    join_response = client.post(
        f"/group/{code}/join",
        json={"name": "Chatter"}
    )
    member_id = join_response.json()["member"]["id"]
    
    # Chat with PlanPal
    response = client.post(
        f"/group/{code}/chat",
        json={"member_id": member_id, "message": "@PlanPal suggest"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["bot_response"] is not None
