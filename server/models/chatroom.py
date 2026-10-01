from server import db
from sqlalchemy import (
    Column,
    Integer,
    Boolean,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from server.models.types import token_column, user_id_column


class Chatroom(db.Model):
    __tablename__ = "chatrooms"

    id = Column(Integer, primary_key=True, nullable=False)
    creator_id = Column(user_id_column(), ForeignKey("users.id"))
    creator = relationship("User", foreign_keys=[creator_id])

    claimant_id = Column(user_id_column(), ForeignKey("users.id"))
    claimant = relationship("User", foreign_keys=[claimant_id])

    code = Column(token_column())

    active = Column(Boolean, nullable=False, default=True)
    status = Column(token_column())

    def __init__(self, user, data, active):
        self.creator = user
        self.code = data["code"]
        self.active = active
        self.status = "unclaimed"

    def update(self, data):
        self.code = data["code"]

    def map(self):
        return {
            "id": self.id,
            "active": self.active,
            "code": self.code,
            "creator": self.creator_id,
            "status": self.status,
            "mentor_name": self.claimant.name if self.claimant else None,
            "mentor_id": self.claimant_id,
        }
