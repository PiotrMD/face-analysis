import os
import json
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database setup
DATABASE_URL = os.getenv('DATABASE_URL', '')
# Railway uses postgres:// but SQLAlchemy requires postgresql://
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
# Fallback to SQLite if URL is missing or invalid
if not DATABASE_URL or not (DATABASE_URL.startswith('postgresql://') or DATABASE_URL.startswith('sqlite://')):
    print(f"[DB] Invalid or missing DATABASE_URL={repr(DATABASE_URL[:40])} — falling back to SQLite", flush=True)
    DATABASE_URL = 'sqlite:///face_analysis.db'
else:
    print(f"[DB] Using DATABASE_URL={DATABASE_URL[:30]}...", flush=True)
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Analysis(Base):
    """Store facial analysis results"""
    __tablename__ = 'analyses'

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(36), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    analysis_result = Column(Text, nullable=True)  # JSON string
    error = Column(Text, nullable=True)  # Error message if validation failed

    def to_dict(self):
        result = None
        if self.analysis_result:
            try:
                result = json.loads(self.analysis_result)
            except json.JSONDecodeError:
                pass
        return {
            'id': self.id,
            'token': self.token,
            'created_at': self.created_at.isoformat(),
            'analysis': result,
            'error': self.error
        }

    @staticmethod
    def get_or_create(token):
        """Get analysis by token or create new"""
        db = SessionLocal()
        try:
            analysis = db.query(Analysis).filter(Analysis.token == token).first()
            if not analysis:
                analysis = Analysis(token=token)
                db.add(analysis)
                db.commit()
                db.refresh(analysis)
            return analysis
        finally:
            db.close()

    @staticmethod
    def save_result(token, result_dict, error=None):
        """Save analysis result to database"""
        db = SessionLocal()
        try:
            analysis = db.query(Analysis).filter(Analysis.token == token).first()
            if not analysis:
                analysis = Analysis(token=token)
                db.add(analysis)

            if error:
                analysis.error = error
            elif result_dict:
                analysis.analysis_result = json.dumps(result_dict, ensure_ascii=False)

            db.commit()
            db.refresh(analysis)
            return analysis
        finally:
            db.close()

    @staticmethod
    def get_by_token(token):
        """Retrieve analysis by token"""
        db = SessionLocal()
        try:
            analysis = db.query(Analysis).filter(Analysis.token == token).first()
            return analysis
        finally:
            db.close()

    @staticmethod
    def count_completed():
        db = SessionLocal()
        try:
            return db.query(Analysis).filter(Analysis.analysis_result.isnot(None)).count()
        finally:
            db.close()


class ContactRequest(Base):
    __tablename__ = 'contact_requests'

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(36), index=True, nullable=True)
    full_name = Column(String(200), nullable=False)
    phone_number = Column(String(50), nullable=False)
    email = Column(String(200), nullable=True)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    @staticmethod
    def save(token, full_name, phone_number, email=None, message=None):
        db = SessionLocal()
        try:
            req = ContactRequest(
                token=token or None,
                full_name=full_name,
                phone_number=phone_number,
                email=email or None,
                message=message or None,
            )
            db.add(req)
            db.commit()
            db.refresh(req)
            return req
        finally:
            db.close()


class FollowUpEmail(Base):
    __tablename__ = 'followup_emails'

    id         = Column(Integer, primary_key=True)
    email      = Column(String(200), nullable=False)
    full_name  = Column(String(200), nullable=False)
    token      = Column(String(36), nullable=True)
    email_type = Column(String(10), nullable=False)   # 'day3' | 'day7'
    send_at    = Column(DateTime, nullable=False)
    sent_at    = Column(DateTime, nullable=True)
    error      = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    @staticmethod
    def schedule(email, full_name, token):
        from datetime import timedelta
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            for email_type, days in [('day3', 3), ('day7', 7)]:
                db.add(FollowUpEmail(
                    email=email, full_name=full_name, token=token,
                    email_type=email_type, send_at=now + timedelta(days=days),
                ))
            db.commit()
        finally:
            db.close()

    @staticmethod
    def get_pending():
        db = SessionLocal()
        try:
            return db.query(FollowUpEmail).filter(
                FollowUpEmail.send_at <= datetime.utcnow(),
                FollowUpEmail.sent_at.is_(None),
                FollowUpEmail.error.is_(None),
            ).all()
        finally:
            db.close()

    def mark_sent(self):
        db = SessionLocal()
        try:
            row = db.query(FollowUpEmail).get(self.id)
            if row:
                row.sent_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()

    def mark_error(self, msg):
        db = SessionLocal()
        try:
            row = db.query(FollowUpEmail).get(self.id)
            if row:
                row.error = str(msg)[:500]
                db.commit()
        finally:
            db.close()


class DiscountCode(Base):
    __tablename__ = 'discount_codes'

    id            = Column(Integer, primary_key=True)
    email         = Column(String(200), nullable=False, index=True)
    result_token  = Column(String(36), nullable=True, index=True)
    discount_code = Column(String(20), nullable=False, default='FACE10')
    created_at    = Column(DateTime, default=datetime.utcnow, nullable=False)
    valid_until   = Column(DateTime, nullable=False)
    used          = Column(Boolean, nullable=False, default=False)

    @staticmethod
    def create(email: str, result_token: str | None = None) -> 'DiscountCode':
        from datetime import timedelta
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            entry = DiscountCode(
                email=email,
                result_token=result_token or None,
                discount_code='FACE10',
                created_at=now,
                valid_until=now + timedelta(days=7),
                used=False,
            )
            db.add(entry)
            db.commit()
            db.refresh(entry)
            return entry
        finally:
            db.close()


def init_db():
    """Initialize database tables, add missing columns to existing tables."""
    Base.metadata.create_all(bind=engine)
    # Migrate: add email column if missing (SQLite doesn't support ALTER TABLE ADD COLUMN IF NOT EXISTS)
    try:
        with engine.connect() as conn:
            conn.execute(__import__('sqlalchemy').text(
                "ALTER TABLE contact_requests ADD COLUMN email VARCHAR(200)"
            ))
            conn.commit()
    except Exception:
        pass  # Column already exists
