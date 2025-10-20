from server import db
from sqlalchemy import Column, Integer, Boolean, Text, String, ForeignKey, ARRAY, DateTime
from sqlalchemy.orm import relationship
from flask import request
from flask import session as flask_session


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
    tags = Column(ARRAY(Text), nullable=False)
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
        self.tags = data["tags"]
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
        self.tags = data["tags"]

    def map(self):
        creator_name = "Unknown User"
        creator_email = ""
        creator_discord = ""
        creator_phone = ""
        creator_preferred = ""
        mentor_name = None

        if self.creator:
            creator_data = self.creator.map()
            creator_name = creator_data.get("name", "User")
            creator_email = creator_data.get("email", "")
            creator_discord = creator_data.get("discord", "")
            creator_phone = creator_data.get("phone", "")
            creator_preferred = creator_data.get("preferred", "")

        if self.claimant_id is not None:
            if flask_session.get('user_id') == str(self.claimant_id):
                mentor_name = flask_session.get('user_name', 'Mentor')
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
            "creator": creator_name,
            "discord": creator_discord,
            "email": creator_email,
            "phone": creator_phone,
            "preferred": creator_preferred,
            "createdAt": self.createdAt,
            "status": self.status,
            "mentor_name": mentor_name,
            "mentor_id": self.claimant_id
        }
