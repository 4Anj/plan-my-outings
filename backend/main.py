from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Field, SQLModel, create_engine, Session, select, Relationship
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel
import os
import random
import string
import httpx
import hashlib
from contextlib import asynccontextmanager

# Database Models
class Group(SQLModel, table=True):
    __tablename__ = "groups"
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True)
    name: str
    mood: Optional[str] = None
    budget_level: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Member(SQLModel, table=True):
    __tablename__ = "members"
    id: Optional[int] = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="groups.id")
    name: str
    avatar_url: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Suggestion(SQLModel, table=True):
    __tablename__ = "suggestions"
    id: Optional[int] = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="groups.id")
    type: str  # 'place'|'movie'|'experience'
    source_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    rating: Optional[float] = None
    price_estimate: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict, sa_column_kwargs={"type_": "JSONB"})
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Poll(SQLModel, table=True):
    __tablename__ = "polls"
    id: Optional[int] = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="groups.id")
    title: str
    options: Dict[str, Any] = Field(default_factory=dict, sa_column_kwargs={"type_": "JSONB"})
    votes: Dict[str, Any] = Field(default_factory=dict, sa_column_kwargs={"type_": "JSONB"})
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_messages"
    id: Optional[int] = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="groups.id")
    member_id: Optional[int] = None
    message: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Request/Response Models
class CreateGroupRequest(BaseModel):
    name: str
    mood: Optional[str] = None
    budget_level: Optional[str] = None

class JoinGroupRequest(BaseModel):
    name: str
    avatar_url: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None

class CreatePollRequest(BaseModel):
    title: str
    options: List[Dict[str, str]]

class VoteRequest(BaseModel):
    member_id: int
    option_id: str
    emoji: str

class ChatRequest(BaseModel):
    member_id: int
    message: str

class BotQueryRequest(BaseModel):
    group_id: int
    text: str

# Database Setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/planmyoutings")
engine = create_engine(DATABASE_URL, echo=True)

def get_session():
    with Session(engine) as session:
        yield session

# Simple cache for API responses
cache: Dict[str, tuple[Any, float]] = {}
CACHE_TTL = 1800  # 30 minutes

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    SQLModel.metadata.create_all(engine)
    yield
    # Cleanup if needed

app = FastAPI(title="Plan My Outings API", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper Functions
def generate_code() -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def get_cache_key(prefix: str, *args) -> str:
    content = f"{prefix}:{'|'.join(map(str, args))}"
    return hashlib.md5(content.encode()).hexdigest()

def get_cached(key: str) -> Optional[Any]:
    if key in cache:
        data, timestamp = cache[key]
        if datetime.now(timezone.utc).timestamp() - timestamp < CACHE_TTL:
            return data
        del cache[key]
    return None

def set_cache(key: str, data: Any):
    cache[key] = (data, datetime.now(timezone.utc).timestamp())

async def fetch_google_places(mood: str, budget_level: str, lat: float = 12.9716, lng: float = 77.5946):
    """Fetch places from Google Places API"""
    api_key = os.getenv("GOOGLE_PLACES_KEY")
    if not api_key:
        return get_mock_places(mood, budget_level)
    
    cache_key = get_cache_key("places", mood, budget_level, lat, lng)
    cached = get_cached(cache_key)
    if cached:
        return cached
    
    # Map mood to place types
    type_map = {
        "adventurous": "tourist_attraction",
        "chill": "cafe",
        "romantic": "restaurant",
        "foodie": "restaurant",
        "fun_getaway": "amusement_park"
    }
    place_type = type_map.get(mood, "point_of_interest")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                params={
                    "location": f"{lat},{lng}",
                    "radius": 5000,
                    "type": place_type,
                    "key": api_key
                },
                timeout=10.0
            )
            data = response.json()
            if data.get("status") == "OK":
                set_cache(cache_key, data["results"][:10])
                return data["results"][:10]
    except Exception as e:
        print(f"Google Places error: {e}")
    
    return get_mock_places(mood, budget_level)

async def fetch_tmdb_movies(mood: str):
    """Fetch movies from TMDb API"""
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        return get_mock_movies(mood)
    
    cache_key = get_cache_key("movies", mood)
    cached = get_cached(cache_key)
    if cached:
        return cached
    
    genre_map = {
        "adventurous": 12,  # Adventure
        "chill": 35,  # Comedy
        "romantic": 10749,  # Romance
        "foodie": 99,  # Documentary
        "fun_getaway": 16  # Animation
    }
    genre_id = genre_map.get(mood, 28)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.themoviedb.org/3/discover/movie",
                params={
                    "api_key": api_key,
                    "with_genres": genre_id,
                    "sort_by": "popularity.desc",
                    "language": "en-IN"
                },
                timeout=10.0
            )
            data = response.json()
            if "results" in data:
                set_cache(cache_key, data["results"][:10])
                return data["results"][:10]
    except Exception as e:
        print(f"TMDb error: {e}")
    
    return get_mock_movies(mood)

def get_mock_places(mood: str, budget_level: str):
    """Mock places data"""
    places = [
        {"name": "Cubbon Park", "rating": 4.5, "price_level": 0, "place_id": "mock_1"},
        {"name": "Wonderla", "rating": 4.3, "price_level": 3, "place_id": "mock_2"},
        {"name": "Cafe Coffee Day", "rating": 4.0, "price_level": 1, "place_id": "mock_3"},
        {"name": "Lalbagh Botanical Garden", "rating": 4.6, "price_level": 0, "place_id": "mock_4"},
    ]
    return places

def get_mock_movies(mood: str):
    """Mock movies data"""
    movies = [
        {"title": "Zindagi Na Milegi Dobara", "vote_average": 8.1, "id": 12345},
        {"title": "Dil Chahta Hai", "vote_average": 8.0, "id": 12346},
        {"title": "Queen", "vote_average": 7.8, "id": 12347},
        {"title": "3 Idiots", "vote_average": 8.4, "id": 12348},
    ]
    return movies

def map_price_level_to_inr(price_level: Optional[int]) -> int:
    """Map Google price_level to INR for 2 people"""
    mapping = {0: 300, 1: 700, 2: 1500, 3: 3000, 4: 4500}
    return mapping.get(price_level or 1, 1000)

def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance in km using Haversine formula"""
    from math import radians, sin, cos, sqrt, atan2
    R = 6371
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def calculate_score(suggestion: Suggestion, group_budget: str, votes: int, max_votes: int, distance_km: float, max_distance: float) -> float:
    """PlanPal scoring algorithm"""
    rating_norm = (suggestion.rating or 3.5) / 5.0
    
    budget_map = {"low": 1000, "medium": 2000, "high": 4000}
    budget_limit = budget_map.get(group_budget, 2000)
    price = suggestion.price_estimate or 1000
    
    if price <= budget_limit:
        budget_match = 1.0
    elif price <= budget_limit * 1.2:
        budget_match = 0.5
    else:
        budget_match = 0.1
    
    vote_score = votes / max_votes if max_votes > 0 else 0.0
    proximity_score = max(0, 1 - (distance_km / max_distance)) if max_distance > 0 else 0.5
    
    score = (rating_norm * 0.5) + (budget_match * 0.2) + (vote_score * 0.2) + (proximity_score * 0.1)
    return score

# API Endpoints
@app.post("/group")
def create_group(req: CreateGroupRequest, session: Session = Depends(get_session)):
    code = generate_code()
    group = Group(code=code, name=req.name, mood=req.mood, budget_level=req.budget_level)
    session.add(group)
    session.commit()
    session.refresh(group)
    
    base_url = os.getenv("BASE_URL", "http://localhost:5173")
    link = f"{base_url}/g/{code}"
    
    return {
        "code": code,
        "link": link,
        "group": {
            "id": group.id,
            "code": group.code,
            "name": group.name,
            "mood": group.mood,
            "budget_level": group.budget_level,
            "created_at": group.created_at.isoformat()
        }
    }

@app.post("/group/{code}/join")
def join_group(code: str, req: JoinGroupRequest, session: Session = Depends(get_session)):
    group = session.exec(select(Group).where(Group.code == code)).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    member = Member(
        group_id=group.id,
        name=req.name,
        avatar_url=req.avatar_url,
        location_lat=req.lat,
        location_lng=req.lng
    )
    session.add(member)
    session.commit()
    session.refresh(member)
    
    return {
        "member": {
            "id": member.id,
            "name": member.name,
            "avatar_url": member.avatar_url,
            "location_lat": member.location_lat,
            "location_lng": member.location_lng,
            "joined_at": member.joined_at.isoformat()
        }
    }

@app.get("/group/{code}")
def get_group(code: str, session: Session = Depends(get_session)):
    group = session.exec(select(Group).where(Group.code == code)).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    members = session.exec(select(Member).where(Member.group_id == group.id)).all()
    suggestions = session.exec(select(Suggestion).where(Suggestion.group_id == group.id)).all()
    polls = session.exec(select(Poll).where(Poll.group_id == group.id)).all()
    
    return {
        "group": {
            "id": group.id,
            "code": group.code,
            "name": group.name,
            "mood": group.mood,
            "budget_level": group.budget_level,
            "created_at": group.created_at.isoformat()
        },
        "members": [
            {
                "id": m.id,
                "name": m.name,
                "avatar_url": m.avatar_url,
                "location_lat": m.location_lat,
                "location_lng": m.location_lng
            } for m in members
        ],
        "suggestions": [
            {
                "id": s.id,
                "type": s.type,
                "title": s.title,
                "description": s.description,
                "rating": s.rating,
                "price_estimate": s.price_estimate,
                "metadata": s.metadata
            } for s in suggestions
        ],
        "polls": [
            {
                "id": p.id,
                "title": p.title,
                "options": p.options,
                "votes": p.votes,
                "created_at": p.created_at.isoformat()
            } for p in polls
        ]
    }

@app.post("/group/{code}/suggestions")
async def create_suggestions(
    code: str,
    source: str = "google",
    session: Session = Depends(get_session)
):
    group = session.exec(select(Group).where(Group.code == code)).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    members = session.exec(select(Member).where(Member.group_id == group.id)).all()
    
    # Calculate centroid
    lats = [m.location_lat for m in members if m.location_lat]
    lngs = [m.location_lng for m in members if m.location_lng]
    centroid_lat = sum(lats) / len(lats) if lats else 12.9716
    centroid_lng = sum(lngs) / len(lngs) if lngs else 77.5946
    
    suggestions = []
    
    if source == "google":
        places = await fetch_google_places(group.mood or "chill", group.budget_level or "medium", centroid_lat, centroid_lng)
        for place in places[:4]:
            suggestion = Suggestion(
                group_id=group.id,
                type="place",
                source_id=place.get("place_id"),
                title=place.get("name", "Unknown Place"),
                description=place.get("vicinity", ""),
                rating=place.get("rating", 4.0),
                price_estimate=map_price_level_to_inr(place.get("price_level")),
                metadata={
                    "location": place.get("geometry", {}).get("location", {}),
                    "types": place.get("types", [])
                }
            )
            session.add(suggestion)
            suggestions.append(suggestion)
    
    elif source == "tmdb":
        movies = await fetch_tmdb_movies(group.mood or "chill")
        for movie in movies[:4]:
            suggestion = Suggestion(
                group_id=group.id,
                type="movie",
                source_id=str(movie.get("id")),
                title=movie.get("title", "Unknown Movie"),
                description=movie.get("overview", ""),
                rating=movie.get("vote_average", 7.0) / 2,  # Convert to 5-star
                price_estimate=600,  # 2 tickets
                metadata={
                    "poster_path": movie.get("poster_path"),
                    "release_date": movie.get("release_date")
                }
            )
            session.add(suggestion)
            suggestions.append(suggestion)
    
    session.commit()
    
    return {
        "suggestions": [
            {
                "id": s.id,
                "type": s.type,
                "title": s.title,
                "rating": s.rating,
                "price_estimate": s.price_estimate
            } for s in suggestions
        ]
    }

@app.get("/group/{code}/suggestions")
def get_suggestions(code: str, session: Session = Depends(get_session)):
    group = session.exec(select(Group).where(Group.code == code)).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    suggestions = session.exec(select(Suggestion).where(Suggestion.group_id == group.id)).all()
    
    return [
        {
            "id": s.id,
            "type": s.type,
            "title": s.title,
            "description": s.description,
            "rating": s.rating,
            "price_estimate": s.price_estimate,
            "metadata": s.metadata
        } for s in suggestions
    ]

@app.post("/group/{code}/polls")
def create_poll(code: str, req: CreatePollRequest, session: Session = Depends(get_session)):
    group = session.exec(select(Group).where(Group.code == code)).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    poll = Poll(
        group_id=group.id,
        title=req.title,
        options={"options": req.options},
        votes={}
    )
    session.add(poll)
    session.commit()
    session.refresh(poll)
    
    return {
        "id": poll.id,
        "title": poll.title,
        "options": poll.options,
        "votes": poll.votes,
        "created_at": poll.created_at.isoformat()
    }

@app.post("/group/{code}/polls/{poll_id}/vote")
def vote_poll(code: str, poll_id: int, req: VoteRequest, session: Session = Depends(get_session)):
    poll = session.exec(select(Poll).where(Poll.id == poll_id)).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    
    votes = poll.votes or {}
    option_id = req.option_id
    
    if option_id not in votes:
        votes[option_id] = []
    
    vote_entry = {"member_id": req.member_id, "emoji": req.emoji}
    votes[option_id].append(vote_entry)
    
    poll.votes = votes
    session.add(poll)
    session.commit()
    session.refresh(poll)
    
    return {
        "id": poll.id,
        "title": poll.title,
        "options": poll.options,
        "votes": poll.votes
    }

@app.post("/group/{code}/chat")
async def post_chat(code: str, req: ChatRequest, session: Session = Depends(get_session)):
    group = session.exec(select(Group).where(Group.code == code)).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    message = ChatMessage(
        group_id=group.id,
        member_id=req.member_id,
        message=req.message
    )
    session.add(message)
    session.commit()
    
    bot_response = None
    if "@PlanPal" in req.message:
        bot_response = await handle_planpal_query(group.id, req.message, session)
    
    return {"ok": True, "bot_response": bot_response}

@app.post("/bot/query")
async def bot_query(req: BotQueryRequest, session: Session = Depends(get_session)):
    reply = await handle_planpal_query(req.group_id, req.text, session)
    return {"reply": reply}

async def handle_planpal_query(group_id: int, text: str, session: Session):
    """Process PlanPal commands"""
    text_lower = text.lower()
    
    suggestions = session.exec(select(Suggestion).where(Suggestion.group_id == group_id)).all()
    if not suggestions:
        return "No suggestions available yet. Add some places or movies first!"
    
    group = session.exec(select(Group).where(Group.id == group_id)).first()
    
    if "suggest" in text_lower:
        # Calculate scores
        scored = []
        for s in suggestions:
            score = calculate_score(s, group.budget_level or "medium", 0, 1, 0, 10)
            scored.append((s, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        top3 = scored[:3]
        
        reply = "🎯 Top picks for you:\n\n"
        for i, (s, score) in enumerate(top3, 1):
            reply += f"{i}. **{s.title}** (Rating: {s.rating}/5)\n"
            reply += f"   ₹{s.price_estimate} for 2 | Score: {score:.2f}\n\n"
        
        return reply
    
    elif "safety" in text_lower:
        return "🚨 Safety tips:\n• Share live location with group\n• Keep emergency contacts handy\n• Travel in daylight when possible\n• Nearest police station: 2.3 km away"
    
    elif "compare" in text_lower:
        if len(suggestions) >= 2:
            s1, s2 = suggestions[0], suggestions[1]
            reply = f"📊 Comparison:\n\n"
            reply += f"**{s1.title}**\nRating: {s1.rating}/5 | ₹{s1.price_estimate}\n\n"
            reply += f"**{s2.title}**\nRating: {s2.rating}/5 | ₹{s2.price_estimate}\n"
            return reply
        return "Need at least 2 suggestions to compare!"
    
    elif "proscons" in text_lower or "pros" in text_lower:
        if suggestions:
            s = suggestions[0]
            reply = f"**{s.title}**\n\n"
            reply += "✅ Pros:\n• Highly rated\n• Within budget\n• Good accessibility\n\n"
            reply += "⚠️ Cons:\n• May be crowded on weekends\n• Limited parking"
            return reply
    
    return "I can help with: suggest, compare, safety, proscons. Just mention me with @PlanPal!"

@app.get("/")
def root():
    return {"message": "Plan My Outings API", "status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
