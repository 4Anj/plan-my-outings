"""
Seed script to create demo data for Plan My Outings
Run with: python seed_data.py
"""
from sqlmodel import Session, create_engine, select
from main import Group, Member, Suggestion, Poll, SQLModel
import os
from datetime import datetime, timezone

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/planmyoutings")
engine = create_engine(DATABASE_URL, echo=True)

def seed_data():
    # Create tables
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        # Clear existing data
        print("Clearing existing data...")
        session.query(Poll).delete()
        session.query(Suggestion).delete()
        session.query(Member).delete()
        session.query(Group).delete()
        session.commit()
        
        # Create demo group
        print("Creating demo group...")
        group = Group(
            code="GFRIEND1",
            name="Friday Fun",
            mood="chill",
            budget_level="low"
        )
        session.add(group)
        session.commit()
        session.refresh(group)
        
        # Create members with realistic Indian city coordinates
        print("Creating members...")
        members_data = [
            {"name": "Rahul", "lat": 12.9716, "lng": 77.5946},  # Bangalore
            {"name": "Priya", "lat": 12.9352, "lng": 77.6245},  # Bangalore
            {"name": "Amit", "lat": 17.3850, "lng": 78.4867},  # Hyderabad
            {"name": "Sneha", "lat": 19.0760, "lng": 72.8777},  # Mumbai
            {"name": "Vikram", "lat": 13.0827, "lng": 80.2707},  # Chennai
        ]
        
        members = []
        for m_data in members_data:
            member = Member(
                group_id=group.id,
                name=m_data["name"],
                location_lat=m_data["lat"],
                location_lng=m_data["lng"]
            )
            session.add(member)
            members.append(member)
        
        session.commit()
        for m in members:
            session.refresh(m)
        
        # Create suggestions (places)
        print("Creating place suggestions...")
        places = [
            {
                "title": "Cubbon Park",
                "description": "Beautiful green space in the heart of the city",
                "rating": 4.5,
                "price_estimate": 300,
                "metadata": {"image": "https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?w=800"}
            },
            {
                "title": "Wonderla Amusement Park",
                "description": "Thrilling rides and water park",
                "rating": 4.3,
                "price_estimate": 3000,
                "metadata": {"image": "https://images.unsplash.com/photo-1594623930572-300a3011d9ae?w=800"}
            },
            {
                "title": "Cafe Coffee Day MG Road",
                "description": "Cozy cafe with great coffee",
                "rating": 4.0,
                "price_estimate": 700,
                "metadata": {"image": "https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=800"}
            },
            {
                "title": "Lalbagh Botanical Garden",
                "description": "Historic botanical garden with diverse flora",
                "rating": 4.6,
                "price_estimate": 200,
                "metadata": {"image": "https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?w=800"}
            }
        ]
        
        for p in places:
            suggestion = Suggestion(
                group_id=group.id,
                type="place",
                source_id=f"place_{p['title'].lower().replace(' ', '_')}",
                title=p["title"],
                description=p["description"],
                rating=p["rating"],
                price_estimate=p["price_estimate"],
                metadata=p["metadata"]
            )
            session.add(suggestion)
        
        # Create movie suggestions
        print("Creating movie suggestions...")
        movies = [
            {
                "title": "Zindagi Na Milegi Dobara",
                "description": "Three friends on a road trip discover themselves",
                "rating": 4.1,
                "price_estimate": 600,
                "metadata": {"poster": "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=800"}
            },
            {
                "title": "Dil Chahta Hai",
                "description": "Coming-of-age story of three friends",
                "rating": 4.0,
                "price_estimate": 600,
                "metadata": {"poster": "https://images.unsplash.com/photo-1598899134739-24c46f58b8c0?w=800"}
            },
            {
                "title": "Queen",
                "description": "A woman goes on her honeymoon alone and finds herself",
                "rating": 3.9,
                "price_estimate": 600,
                "metadata": {"poster": "https://images.unsplash.com/photo-1574267432644-f2f2f5e85f5d?w=800"}
            },
            {
                "title": "3 Idiots",
                "description": "Comedy-drama about engineering students",
                "rating": 4.2,
                "price_estimate": 600,
                "metadata": {"poster": "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=800"}
            }
        ]
        
        for m in movies:
            suggestion = Suggestion(
                group_id=group.id,
                type="movie",
                source_id=f"movie_{m['title'].lower().replace(' ', '_')}",
                title=m["title"],
                description=m["description"],
                rating=m["rating"],
                price_estimate=m["price_estimate"],
                metadata=m["metadata"]
            )
            session.add(suggestion)
        
        # Create experience suggestions
        print("Creating experience suggestions...")
        experiences = [
            {
                "title": "Beach Cleanup Volunteer",
                "description": "Help clean Marina Beach and protect marine life",
                "rating": 4.7,
                "price_estimate": 0,
                "metadata": {
                    "time_commitment": "3 hours",
                    "perks": "Free lunch + certificate",
                    "image": "https://images.unsplash.com/photo-1618477461853-cf6ed80faba5?w=800"
                }
            },
            {
                "title": "Heritage Walking Tour",
                "description": "Free guided tour of Old Bangalore architecture",
                "rating": 4.4,
                "price_estimate": 0,
                "metadata": {
                    "time_commitment": "2 hours",
                    "perks": "Free guide + refreshments",
                    "image": "https://images.unsplash.com/photo-1583422409516-2895a77efded?w=800"
                }
            },
            {
                "title": "Community Kitchen Help",
                "description": "Volunteer at local community kitchen",
                "rating": 4.8,
                "price_estimate": 0,
                "metadata": {
                    "time_commitment": "4 hours",
                    "perks": "Free meals + community",
                    "image": "https://images.unsplash.com/photo-1593113646773-028c131a4cae?w=800"
                }
            },
            {
                "title": "Sunday Art Fair",
                "description": "Free entry to local artist exhibitions",
                "rating": 4.2,
                "price_estimate": 0,
                "metadata": {
                    "time_commitment": "1-3 hours",
                    "perks": "Meet artists + live music",
                    "image": "https://images.unsplash.com/photo-1460661419201-fd4cecdf8a8b?w=800"
                }
            }
        ]
        
        for e in experiences:
            suggestion = Suggestion(
                group_id=group.id,
                type="experience",
                source_id=f"exp_{e['title'].lower().replace(' ', '_')}",
                title=e["title"],
                description=e["description"],
                rating=e["rating"],
                price_estimate=e["price_estimate"],
                metadata=e["metadata"]
            )
            session.add(suggestion)
        
        session.commit()
        
        # Get all suggestions for polls
        all_suggestions = session.exec(select(Suggestion).where(Suggestion.group_id == group.id)).all()
        
        # Create polls
        print("Creating polls...")
        poll1 = Poll(
            group_id=group.id,
            title="Where should we go this weekend?",
            options={
                "options": [
                    {"id": "opt1", "title": all_suggestions[0].title},
                    {"id": "opt2", "title": all_suggestions[1].title},
                    {"id": "opt3", "title": all_suggestions[2].title}
                ]
            },
            votes={
                "opt1": [
                    {"member_id": members[0].id, "emoji": "👍"},
                    {"member_id": members[1].id, "emoji": "❤️"}
                ],
                "opt2": [
                    {"member_id": members[2].id, "emoji": "🔥"}
                ],
                "opt3": [
                    {"member_id": members[3].id, "emoji": "👍"},
                    {"member_id": members[4].id, "emoji": "😆"}
                ]
            }
        )
        session.add(poll1)
        
        poll2 = Poll(
            group_id=group.id,
            title="Movie night pick?",
            options={
                "options": [
                    {"id": "mov1", "title": all_suggestions[4].title},
                    {"id": "mov2", "title": all_suggestions[5].title}
                ]
            },
            votes={
                "mov1": [
                    {"member_id": members[0].id, "emoji": "❤️"},
                    {"member_id": members[2].id, "emoji": "❤️"},
                    {"member_id": members[4].id, "emoji": "🔥"}
                ],
                "mov2": [
                    {"member_id": members[1].id, "emoji": "👍"}
                ]
            }
        )
        session.add(poll2)
        
        session.commit()
        
        print("\n✅ Seed data created successfully!")
        print(f"Group Code: {group.code}")
        print(f"Group Name: {group.name}")
        print(f"Members: {len(members)}")
        print(f"Suggestions: {len(all_suggestions)}")
        print(f"Polls: 2")
        frontend_port = os.getenv("FRONTEND_PORT", "3000")
        print(f"\nAccess the group at: http://localhost:{frontend_port}/g/{group.code}")


if __name__ == "__main__":
    seed_data()
