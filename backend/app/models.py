"""ORM models."""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base
from pgvector.sqlalchemy import Vector


class Event(Base):
    """Event model for managing events."""
    __tablename__ = "event"
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    name = Column(String, nullable=False)
    total_tables = Column(Integer, nullable=False)
    ppl_per_table = Column(Integer, nullable=False)
    chaos_temp = Column(Float, nullable=False)
    
    # Relationship to attendees
    attendees = relationship("EventAttendee", back_populates="event")
    
    def __repr__(self):
        return f"<Event(id={self.id}, name={self.name})>"


class EventAttendee(Base):
    """Event attendee model."""
    __tablename__ = "event_attendee"
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String, nullable=False)
    table_no = Column(Integer, nullable=True)
    seat_no = Column(Integer, nullable=True)
    event_id = Column(Integer, ForeignKey("event.id"), nullable=False)
    rsvp = Column(Boolean, nullable=False, default=False)
    going = Column(Boolean, nullable=False, default=False)
    
    # Relationships
    event = relationship("Event", back_populates="attendees")
    facts = relationship("Fact", back_populates="attendee")
    opinions = relationship("JoinedOpinion", back_populates="attendee")
    
    def __repr__(self):
        return f"<EventAttendee(id={self.id}, name={self.name})>"


class Fact(Base):
    """Fact model for storing attendee facts."""
    __tablename__ = "fact"
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    fact = Column(String, nullable=False)
    attendee_id = Column(Integer, ForeignKey("event_attendee.id"), nullable=False)
    embedding = Column(Vector(768), nullable=True)  # 768 dimensions for Gemini embeddings
    
    # Relationship
    attendee = relationship("EventAttendee", back_populates="facts")
    
    def __repr__(self):
        return f"<Fact(id={self.id}, attendee_id={self.attendee_id})>"


class Opinion(Base):
    """Opinion model for storing opinion questions."""
    __tablename__ = "opinion"
    
    opinion_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    opinion = Column(String, nullable=False)
    
    # Relationship
    joined_opinions = relationship("JoinedOpinion", back_populates="opinion")
    
    def __repr__(self):
        return f"<Opinion(id={self.opinion_id}, opinion={self.opinion})>"


class JoinedOpinion(Base):
    """JoinedOpinion model for storing attendee responses to opinions."""
    __tablename__ = "joined_opinion"
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    attendee_id = Column(Integer, ForeignKey("event_attendee.id"), nullable=False)
    opinion_id = Column(Integer, ForeignKey("opinion.opinion_id"), nullable=False)
    answer = Column(String, nullable=False)
    
    # Relationships
    attendee = relationship("EventAttendee", back_populates="opinions")
    opinion = relationship("Opinion", back_populates="joined_opinions")
    
    def __repr__(self):
        return f"<JoinedOpinion(attendee_id={self.attendee_id}, opinion_id={self.opinion_id})>"
