from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Text, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from sqlalchemy import Boolean


Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)
    username = Column(String, nullable=True)
    age_group = Column(String)  # '1-4', '5-8', '9-11'
    created_at = Column(DateTime, default=datetime.utcnow)

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger)
    user_name = Column(String)
    message_id = Column(BigInteger)
    admin_chat_message_id = Column(BigInteger)
    text = Column(Text)
    status = Column(String, default='pending')
    answer = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    answered_at = Column(DateTime, nullable=True)

class QuizResult(Base):
    __tablename__ = "quiz_results"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger)
    sdg_id = Column(Integer)
    difficulty = Column(String)
    age_group = Column(String)  # '1-4', '5-8', '9-11'
    score = Column(Integer)
    total = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('user_id', 'sdg_id', 'difficulty', 'age_group', 
                       name='uq_user_sdg_diff_age'),
    )

class GameResult(Base):
    __tablename__ = "game_results"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger)
    game_type = Column(String)  # 'waste', 'habits', 'rightwrong', 'story'
    age_group = Column(String)  # '1-4', '5-8', '9-11'
    difficulty = Column(String, nullable=True)
    score = Column(Integer)
    max_score = Column(Integer)
    steps_completed = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('user_id', 'game_type', 'age_group', name='uq_user_game_age'),
    )

class AmbassadorApplication(Base):
    __tablename__ = "ambassador_applications"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger)
    full_name = Column(String)
    age = Column(Integer)
    institution = Column(String)
    city = Column(String)
    contact = Column(String)
    role = Column(String)
    status = Column(String, default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)

class Feedback(Base):
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger)
    sdg_id = Column(Integer, nullable=True)
    usefulness = Column(Integer)
    interest = Column(Integer)
    clarity = Column(Integer)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class StorySave(Base):
    __tablename__ = "story_saves"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger)
    save_data = Column(Text)  # JSON с данными сохранения
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('user_id', name='uq_user_story_save'),
    )

class UserActivity(Base):
    __tablename__ = "user_activity"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger)
    action = Column(String)
    target_id = Column(Integer, nullable=True)
    details = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class VideoContest(Base):
    __tablename__ = "video_contest"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger)
    username = Column(String, nullable=True)
    video_file_id = Column(String)  # Сюда сохраним ID видео
    description = Column(Text, nullable=True)
    status = Column(String, default='pending')  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)

class SDGContent(Base):
    __tablename__ = "sdg_content"
    
    id = Column(Integer, primary_key=True)
    sdg_id = Column(Integer) # От 1 до 17
    age_group = Column(String) # '1-4', '5-8', '9-11' или 'all'
    description = Column(Text)
    video_url = Column(String, nullable=True)
    
    __table_args__ = (
        UniqueConstraint('sdg_id', 'age_group', name='uq_sdg_age'),
    )

class BotSettings(Base):
    __tablename__ = "bot_settings"
    
    id = Column(Integer, primary_key=True, default=1)
    is_contest_active = Column(Boolean, default=True) # Включен ли конкурс