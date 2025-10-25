# Plan My Outings - Backend API

FastAPI backend for Plan My Outings group planning app.

## Tech Stack

- **Python 3.11+**
- **FastAPI** - Modern async web framework
- **SQLModel** - SQL databases with Python type hints
- **PostgreSQL** - Primary database
- **Docker** - Containerization
- **Uvicorn** - ASGI server

## Features

- Group creation with shareable codes
- Member management with geolocation
- Suggestions (places, movies, experiences)
- Emoji-based polling system
- PlanPal AI chatbot (rule-based + optional OpenAI)
- External API integration (Google Places, TMDb, Unsplash)
- Response caching to respect API quotas

## Setup Instructions

### Local Development with Docker (Recommended)

1. **Clone the repository**
```bash
git clone <backend-repo-url>
cd plan-my-outings-backend
```

2. **Create `.env` file**
```bash
cp .env.sample .env
```

Edit `.env` with your API keys (optional for MVP):
```env
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/planmyoutings
BASE_URL=http://localhost:5173
GOOGLE_PLACES_KEY=your_key_here
TMDB_API_KEY=your_key_here
UNSPLASH_KEY=your_key_here
OPENAI_KEY=your_key_here
```

3. **Start services**
```bash
docker-compose up --build
```

The API will be available at `http://localhost:8000`

4. **Seed demo data**
```bash
# In a new terminal
docker-compose exec api python seed_data.py
```

### Manual Setup (Without Docker)

1. **Install PostgreSQL 15+**

2. **Create database**
```bash
createdb planmyoutings
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set environment variables**
```bash
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/planmyoutings
export BASE_URL=http://localhost:5173
```

5. **Run the server**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

6. **Seed data**
```bash
python seed_data.py
```

## API Documentation

Once running, visit:
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Groups

#### POST /group
Create a new group.

**Request:**
```json
{
  "name": "Friday Night",
  "mood": "chill",
  "budget_level": "low"
}
```

**Response:**
```json
{
  "code": "AB12CD",
  "link": "http://localhost:5173/g/AB12CD",
  "group": {
    "id": 1,
    "code": "AB12CD",
    "name": "Friday Night",
    "mood": "chill",
    "budget_level": "low",
    "created_at": "2025-01-15T10:30:00Z"
  }
}
```

#### POST /group/{code}/join
Join an existing group.

**Request:**
```json
{
  "name": "Riya",
  "avatar_url": "https://...",
  "lat": 12.9716,
  "lng": 77.5946
}
```

#### GET /group/{code}
Get group details with members, suggestions, and polls.

### Suggestions

#### POST /group/{code}/suggestions?source=google|tmdb
Fetch suggestions from external APIs.

**Query Parameters:**
- `source`: `google` (places) or `tmdb` (movies)

#### GET /group/{code}/suggestions
List all suggestions for a group.

### Polls

#### POST /group/{code}/polls
Create a new poll.

**Request:**
```json
{
  "title": "Pick a cafe",
  "options": [
    {"id": "opt1", "title": "Cafe Mocha"},
    {"id": "opt2", "title": "Starbucks"}
  ]
}
```

#### POST /group/{code}/polls/{poll_id}/vote
Vote on a poll option.

**Request:**
```json
{
  "member_id": 5,
  "option_id": "opt1",
  "emoji": "❤️"
}
```

### Chat & Bot

#### POST /group/{code}/chat
Send a chat message (triggers PlanPal if mentioned).

**Request:**
```json
{
  "member_id": 5,
  "message": "@PlanPal suggest"
}
```

**Response:**
```json
{
  "ok": true,
  "bot_response": "🎯 Top picks for you:\n\n1. **Cubbon Park** (Rating: 4.5/5)..."
}
```

#### POST /bot/query
Direct bot query.

**Request:**
```json
{
  "group_id": 12,
  "text": "suggest"
}
```

## PlanPal Bot Commands

The bot responds to these commands:

- `@PlanPal suggest` - Get top 3 recommendations
- `@PlanPal compare A B` - Compare two options
- `@PlanPal safety` - Safety tips and nearest police station
- `@PlanPal proscons` - Pros and cons of top option

### Scoring Algorithm

```
score = (rating_normalized * 0.5) + 
        (budget_match * 0.2) + 
        (vote_score_normalized * 0.2) + 
        (proximity_score * 0.1)
```

Where:
- `rating_normalized` = rating / 5
- `budget_match` = 1.0 if within budget, 0.5 if slightly over, 0.1 otherwise
- `vote_score_normalized` = votes_for_option / max_votes
- `proximity_score` = 1 - (distance_km / max_distance_km)

## Database Schema

### tables
- `groups` - Group information
- `members` - Group members with location
- `suggestions` - Places, movies, experiences
- `polls` - Poll questions and options
- `chat_messages` - Chat history

See SQL schema in migration files or check `main.py` for SQLModel definitions.

## Testing

Run tests with pytest:

```bash
# With Docker
docker-compose exec api pytest

# Without Docker
pytest
```

Run specific test:
```bash
pytest test_main.py::test_create_group -v
```

## Deployment to Render

### Using Docker (Recommended)

1. **Push code to GitHub**

2. **Create New Web Service on Render**
   - Connect your GitHub repository
   - Name: `planmyoutings-api`
   - Environment: `Docker`
   - Region: Choose closest to your users

3. **Add Environment Variables**
   ```
   DATABASE_URL=<your-render-postgres-url>
   BASE_URL=https://your-frontend.vercel.app
   GOOGLE_PLACES_KEY=<optional>
   TMDB_API_KEY=<optional>
   UNSPLASH_KEY=<optional>
   OPENAI_KEY=<optional>
   ```

4. **Create Render PostgreSQL Database**
   - Create new PostgreSQL instance
   - Copy Internal Database URL
   - Use as DATABASE_URL in web service

5. **Deploy**
   - Render will build from Dockerfile
   - Wait for deployment to complete

6. **Seed Data**
   ```bash
   # Use Render Shell
   python seed_data.py
   ```

### Health Check

Once deployed, verify:
```bash
curl https://your-api.onrender.com/
```

Should return:
```json
{"message": "Plan My Outings API", "status": "running"}
```

## API Rate Limiting & Caching

- External API responses cached for 30 minutes
- In-memory cache (consider Redis for production)
- Automatic fallback to mock data if APIs unavailable
- Respects rate limits with exponential backoff

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| DATABASE_URL | Yes | PostgreSQL connection string |
| BASE_URL | Yes | Frontend URL for group links |
| GOOGLE_PLACES_KEY | No | Google Places API key |
| TMDB_API_KEY | No | The Movie Database API key |
| UNSPLASH_KEY | No | Unsplash API key for images |
| OPENAI_KEY | No | OpenAI API key for enhanced PlanPal |

## Sample Data

The seed script creates:
- 1 demo group (code: `GFRIEND1`)
- 5 members from various Indian cities
- 12 suggestions (4 places, 4 movies, 4 experiences)
- 2 polls with votes

Access: `http://localhost:5173/g/GFRIEND1`

## Troubleshooting

### Database Connection Issues
```bash
# Check if Postgres is running
docker-compose ps

# View logs
docker-compose logs postgres

# Restart services
docker-compose restart
```

### API Not Responding
```bash
# Check API logs
docker-compose logs api

# Restart API only
docker-compose restart api
```

### Port Already in Use
```bash
# Change port in docker-compose.yml
# ports:
#   - "8001:8000"  # Use 8001 instead
```

## Development

### Adding New Endpoints

1. Define request/response models
2. Add endpoint in `main.py`
3. Write tests in `test_main.py`
4. Update this README

### Database Migrations

For schema changes:
1. Modify models in `main.py`
2. Tables auto-create on startup (SQLModel)
3. For production, use Alembic for migrations

## Performance Notes

- Async/await throughout for non-blocking I/O
- Database connection pooling
- API response caching
- Can handle 50+ concurrent users in demo mode
- For production: add Redis, connection pools, load balancing

## Security Notes

- CORS configured (update for production domains)
- No authentication in MVP (add JWT for production)
- API keys stored in environment variables
- Input validation with Pydantic
- SQL injection protection via SQLModel ORM

## License

MIT

## Support

For issues or questions, create an issue on GitHub.
