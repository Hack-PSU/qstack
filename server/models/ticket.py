from server import db
from sqlalchemy import Column, Integer, Boolean, Text, String, ForeignKey, ARRAY, DateTime
from sqlalchemy.orm import relationship


class Ticket(db.Model):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, nullable=False)
    creator_id = Column(String, ForeignKey("users.id"))
    creator = relationship("User", foreign_keys=[creator_id])

    claimant_id = Column(String, ForeignKey("users.id"))
    claimant = relationship("User", foreign_keys=[claimant_id])
    claimant_name = Column(Text)

    question = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    location = Column(Text, nullable=False)
    tags = Column(ARRAY(Text), nullable=False, default=[])
    images = Column(ARRAY(Text), nullable=False)
    creator_email = Column(Text, nullable=False)
    creator_name = Column(Text, nullable=False)

    active = Column(Boolean, nullable=False, default=True)
    status = Column(String)

    createdAt = Column(DateTime, nullable=False)
    claimedAt = Column(DateTime)

    def __init__(self, user, data, active, creator_email="", creator_name=""):
        self.creator = user
        self.question = data["question"]
        self.content = data["content"]
        self.location = data["location"]
        self.tags = data.get("tags", [])
        self.images = data.get("images", [])
        self.creator_email = creator_email
        self.creator_name = creator_name
        self.active = active
        self.createdAt = db.func.now()
        self.status = "unclaimed"
        self.claimedAt = None
        self.claimant_name = None

    def update(self, data):
        self.question = data["question"]
        self.content = data["content"]
        self.location = data["location"]
        self.images = data.get("images", [])
        self.tags = data.get("tags", [])

    def map(self):
        # Use stored creator name (captured at ticket creation)
        creator_name = self.creator_name if self.creator_name else "Unknown User"

        # Get creator contact info from the User relationship
        creator_email = ""
        creator_discord = ""
        creator_phone = ""
        creator_preferred = ""

        if self.creator:
            creator_data = self.creator.map()
            creator_email = creator_data.get("email", "")
            creator_discord = creator_data.get("discord", "")
            creator_phone = creator_data.get("phone", "")
            creator_preferred = creator_data.get("preferred", "")

        # Use stored mentor name (captured when ticket was claimed)
        mentor_name = self.claimant_name if self.claimant_name else None
        if not self.claimant_name and self.claimant_id:
            mentor_name = "Mentor"

        return {
            "id": self.id,
            "question": self.question,
            "active": self.active,
            "content": self.content,
            "tags": self.tags,
            "location": self.location,
            "images": self.images,
            # This is now the true creator's name, stored at ticket creation
            "creator": creator_name,
            "creator_email": self.creator_email,
            "discord": creator_discord,
            "email": creator_email,
            "phone": creator_phone,
            "preferred": creator_preferred,
            "createdAt": self.createdAt,
            "status": self.status,
            # This is now the true mentor's name, stored when ticket was claimed
            "mentor_name": mentor_name,
            "mentor_id": self.claimant_id
        }
