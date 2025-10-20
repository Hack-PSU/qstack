from server import db
from sqlalchemy import Column, Integer, Boolean, Text, String, ForeignKey, ARRAY, DateTime
from sqlalchemy.orm import relationship
from flask import request


class Ticket(db.Model):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, nullable=False)
    creator_id = Column(String, ForeignKey("users.id"))
    creator = relationship("User", foreign_keys=[creator_id])

    claimant_id = Column(String, ForeignKey("users.id"))
    claimant = relationship("User", foreign_keys=[claimant_id])

    question = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    location = Column(Text, nullable=False)
    tags = Column(ARRAY(Text), nullable=False, default=[])
    images = Column(ARRAY(Text), nullable=False)

    active = Column(Boolean, nullable=False, default=True)
    status = Column(String)

    createdAt = Column(DateTime, nullable=False)
    claimedAt = Column(DateTime)

    def __init__(self, user, data, active):
        self.creator = user
        self.question = data["question"]
        self.content = data["content"]
        self.location = data["location"]
        self.tags = data.get("tags", [])
        self.images = data.get("images", [])
        self.active = active
        self.createdAt = db.func.now()
        self.status = "unclaimed"
        self.claimedAt = None

    def update(self, data):
        self.question = data["question"]
        self.content = data["content"]
        self.location = data["location"]
        self.images = data.get("images", [])
        self.tags = data.get("tags", [])

    def map(self):
        from server.hackpsu_api import get_user_info


        # Fetch the creator's name from the HackPSU API using creator_id
        creator_name = "Unknown User"
        if self.creator_id:
            info = get_user_info([str(self.creator_id)])
            if info and str(self.creator_id) in info:
                creator_name = info[str(self.creator_id)].get('name', 'Unknown User')

        # Also fetch mentor's name from HackPSU API for consistency
        mentor_name = None
        if self.claimant_id:
            info = get_user_info([str(self.claimant_id)])
            if info and str(self.claimant_id) in info:
                mentor_name = info[str(self.claimant_id)].get('name', 'Mentor')
            else:
                mentor_name = "Mentor"

        return {
            "id": self.id,
            "question": self.question,
            "active": self.active,
            "content": self.content,
            "tags": self.tags,
            "location": self.location,
            "images": self.images,
            # This is now the true creator's name, not the session user's name
            "creator": creator_name,
            "discord": self.creator.discord if self.creator else "",
            "createdAt": self.createdAt,
            "status": self.status,
            # This is now the true mentor's name, not the session user's name
            "mentor_name": mentor_name,
            "mentor_id": self.claimant_id
        }
