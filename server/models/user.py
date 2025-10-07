from server import db
from sqlalchemy import (
    Column,
    Integer,
    Text,
    ForeignKey,
    ARRAY,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.mutable import MutableList
from flask import session
from server.hackpsu_api import get_user_info, get_my_info


class User(db.Model):
    __tablename__ = "users"

    id = Column(String, primary_key=True, nullable=False)
    role = Column(Text, nullable=False)
    location = Column(Text, nullable=False)
    zoomlink = Column(Text, nullable=False)
    discord = Column(Text, nullable=False)
    resolved_tickets = Column(Integer)
    ratings = Column(MutableList.as_mutable(ARRAY(Numeric(2, 1))))
    reviews = Column(MutableList.as_mutable(ARRAY(Text)), nullable=False)

    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="SET NULL"))
    ticket = relationship("Ticket", foreign_keys=[ticket_id])

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        self.role = kwargs.get('role', 'hacker')
        self.location = "in person"
        self.zoomlink = ""
        self.discord = ""
        self.resolved_tickets = 0
        self.ratings = []
        self.reviews = []

    def map(self):
        # Get name and email from HackPSU API
        name = 'User'
        email = ''

        # Try to fetch user info from HackPSU API (uses Bearer token automatically)
        if self.role in ['mentor', 'admin']:
            # For organizers, fetch from organizer endpoint
            user_info = get_user_info([self.id])
            if self.id in user_info:
                info = user_info[self.id]
                name = info.get('name', 'User')
                email = info.get('email', '')
        else:
            # For regular users, fetch their own info
            user_info = get_my_info()
            if user_info:
                name = user_info.get('name', 'User')
                email = user_info.get('email', '')

        # Fallback to session if API call failed
        if name == 'User':
            name = session.get('user_name', 'User')
        if not email:
            email = session.get('user_email', '')

        return {
            "id": self.id,
            "name": name,
            "email": email,
            "role": self.role,
            "location": self.location,
            "zoomlink": self.zoomlink,
            "discord": self.discord,
            "resolved_tickets": (
                self.resolved_tickets if self.role == "mentor" else "Not Applicable"
            ),
            "ratings": (
                sum(self.ratings) / len(self.ratings)
                if self.role == "mentor" and self.ratings and len(self.ratings) != 0
                else None
            ),
            "reviews": self.reviews if self.reviews != None else [],
        }
