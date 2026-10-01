"""
Column types that mean the same thing on PostgreSQL and MySQL.

QStack's models were written against PostgreSQL and use types MySQL cannot
express at all, which blocks the move to the shared Cloud SQL instance:

* ``ARRAY`` has no MySQL equivalent -- SQLAlchemy cannot even render the type
  ("can't render element of type ARRAY"). JSON exists on both engines and
  behaves like a list from Python, which is all the controllers ever needed.

* ``String`` with no length cannot be rendered on MySQL either ("VARCHAR
  requires a length"), and ``users.id`` is a primary key. Lengths here come
  from the real shape of the data rather than being picked arbitrarily.
"""

from sqlalchemy import JSON, String
from sqlalchemy.ext.mutable import MutableList

# Firebase UIDs are 28 characters. 128 leaves room while staying narrow enough
# to index as a primary key and to be referenced by foreign keys.
USER_ID_LENGTH = 128

# Short internal tokens: ticket status, chatroom code.
TOKEN_LENGTH = 64

# Longest of 'Email', 'Phone', 'Discord', with room to add another.
CONTACT_METHOD_LENGTH = 16


def user_id_column():
    return String(USER_ID_LENGTH)


def token_column():
    return String(TOKEN_LENGTH)


def JsonList():
    """
    A list persisted as JSON.

    MutableList makes in-place mutation tracked, so the existing
    ``mentor.ratings.append(...)`` style keeps working -- a plain JSON column
    would silently drop those appends because SQLAlchemy would never see the
    attribute being set.
    """
    return MutableList.as_mutable(JSON)
