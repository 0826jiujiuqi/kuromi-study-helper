from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Date, Boolean, Time
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from database import Base

db = SQLAlchemy()

class KaoyanConfig(db.Model):
    __tablename__ = "kaoyan_config"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False, unique=True)
    subjects = db.Column(db.Text, nullable=True)
    sprint_date = db.Column(db.String(30), nullable=True)
    daily_hour = db.Column(db.Float, nullable=True)
    math_task = db.Column(db.Text, nullable=True)
    english_task = db.Column(db.Text, nullable=True)
    politics_task = db.Column(db.Text, nullable=True)
    major_task = db.Column(db.Text, nullable=True)
    buffer_day = db.Column(db.Integer, default=1)
    time_prefer = db.Column(db.Text, nullable=True)
    weak_subject = db.Column(db.Text, nullable=True)
    create_time = db.Column(db.DateTime, default=datetime.now)
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class KaoyanDailyRecord(db.Model):
    __tablename__ = "kaoyan_daily_record"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    record_date = db.Column(db.String(20), nullable=False)
    phase_text = db.Column(db.String(50), nullable=True)
    finish_rate = db.Column(db.String(20), default="0%")
    plan_strategy = db.Column(db.Text, nullable=True)
    weak_tip = db.Column(db.Text, nullable=True)
    daily_tasks = db.Column(db.Text, nullable=True)
    feedback = db.Column(db.Text, nullable=True)
    create_time = db.Column(db.DateTime, default=datetime.now)

class StudyEvent(Base):
    __tablename__ = 'study_events'
    id = Column(Integer, primary_key=True)
    date = Column(Date, default=datetime.now().date)
    subject = Column(String(20))
    topic = Column(String(200))
    activity = Column(String(20))
    duration = Column(Integer)
    note = Column(Text, default='')

class KnowledgeNode(Base):
    __tablename__ = 'knowledge_nodes'
    id = Column(Integer, primary_key=True)
    subject = Column(String(20))
    topic = Column(String(200), unique=True)
    last_review = Column(Date)
    next_review = Column(Date)
    mastery = Column(Float, default=0.0)
    prereq = Column(String(200))

class UserGoal(Base):
    __tablename__ = 'user_goals'
    id = Column(Integer, primary_key=True)
    subject = Column(String(20), unique=True)
    one_round_end = Column(Date)
    practice_start = Column(Date)
    current_phase = Column(Text, default='')
    phase_start = Column(Date)
    phase_end = Column(Date)

class DailyPlan(Base):
    __tablename__ = 'daily_plans'
    id = Column(Integer, primary_key=True)
    date = Column(Date, unique=True)
    plan_text = Column(Text)
    completed = Column(Boolean, default=False)
    completion_rate = Column(Float, default=0.0)

class SleepRecord(Base):
    __tablename__ = 'sleep_records'
    id = Column(Integer, primary_key=True)
    date = Column(Date, unique=True)
    bed_time = Column(Time)
    wake_time = Column(Time)
    nap_duration = Column(Integer)
    efficiency = Column(Float, default=0.0)

class StateEvent(Base):
    __tablename__ = 'state_events'
    id = Column(Integer, primary_key=True)
    datetime = Column(DateTime, default=datetime.now)
    state = Column(String(20))
    advice = Column(Text, default='')
    feedback = Column(String(10), default='')

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    subject = Column(String(20))
    phase = Column(String(50))
    description = Column(String(200))
    plan_date = Column(Date)
    actual_date = Column(Date, nullable=True)
    status = Column(String(20), default='未开始')
    created_at = Column(DateTime, default=datetime.now)

class KnowledgePoint(Base):
    __tablename__ = 'knowledge_points'
    id = Column(Integer, primary_key=True)
    subject = Column(String(20))
    title = Column(String(200))
    status = Column(String(20), default='未学')
    priority = Column(Integer, default=0)
    importance = Column(Float, default=0.0)
    source = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)

class StudyPlanConfig(Base):
    __tablename__ = "study_plan_config"
    id = Column(Integer, primary_key=True)
    sprint_start_date = Column(String(20), nullable=False)
    daily_study_hours = Column(Float, nullable=False)
    subject_weights = Column(Text, nullable=False)
    buffer_ratio = Column(Float, default=0.1)

class PlanTask(Base):
    __tablename__ = "plan_tasks"
    id = Column(Integer, primary_key=True)
    subject = Column(String(50), nullable=False)
    task_name = Column(String(100), nullable=False)
    total_amount = Column(Integer, nullable=False)
    unit = Column(String(20), nullable=False)
    unit_size = Column(Integer, default=1)
    unit_hours = Column(Float, nullable=False)
    phase = Column(String(20), default="current")

class DailyTask(Base):
    __tablename__ = 'daily_tasks'
    id = Column(Integer, primary_key=True)
    date = Column(Date)
    content = Column(String(200))
    completed = Column(Boolean, default=False)

class StageTask(Base):
    __tablename__ = 'stage_tasks'
    id = Column(Integer, primary_key=True)
    title = Column(String(200))
    deadline = Column(Date)
    progress = Column(Float, default=0.0)
    completed = Column(Boolean, default=False)

class StatusReport(Base):
    __tablename__ = 'status_reports'
    id = Column(Integer, primary_key=True)
    date = Column(Date)
    content = Column(Text)
    feedback = Column(Text)
