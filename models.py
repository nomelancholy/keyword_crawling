from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, index=True)
    keyword = Column(String)
    interval_minutes = Column(Integer)
    is_active = Column(Boolean, default=True)
    last_checked = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    alerts = relationship("Alert", back_populates="task", cascade="all, delete-orphan")
    links = relationship("TaskLink", back_populates="task", cascade="all, delete-orphan")

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    found_at = Column(DateTime, default=datetime.utcnow)
    context = Column(String)  # Short snippet where keyword was found
    
    task = relationship("Task", back_populates="alerts")

class TaskLink(Base):
    __tablename__ = "task_links"
    __table_args__ = (
        UniqueConstraint("task_id", "url", name="uq_task_links_task_id_url"),
    )

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    url = Column(String, index=True)
    first_seen = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="links")
