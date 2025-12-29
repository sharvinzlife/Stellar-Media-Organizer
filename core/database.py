"""
Database models and session management for job history tracking
Uses SQLite for lightweight, cross-platform persistence
"""
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

Base = declarative_base()


class JobStatus(str, Enum):
    """Job status enum"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    """Job type enum"""
    ORGANIZE = "organize"
    FILTER_AUDIO = "filter_audio"
    CONVERT = "convert"
    BOTH = "both"  # organize + filter


class Job(Base):
    """Job history table"""
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_type = Column(SQLEnum(JobType), nullable=False)
    status = Column(SQLEnum(JobStatus), nullable=False, default=JobStatus.PENDING)
    
    # File information
    input_path = Column(String(500), nullable=False)
    output_path = Column(String(500), nullable=True)
    filename = Column(String(255), nullable=True)
    
    # Processing details
    language = Column(String(50), nullable=True)  # For audio filtering
    volume_boost = Column(Float, nullable=True)
    conversion_preset = Column(String(50), nullable=True)
    
    # Progress tracking
    progress = Column(Float, default=0.0)  # 0.0 to 100.0
    current_file = Column(String(255), nullable=True)
    total_files = Column(Integer, default=0)
    processed_files = Column(Integer, default=0)
    
    # Enhanced progress tracking
    phase = Column(String(50), default="pending")  # pending, downloading, filtering, organizing, uploading, scanning, completed
    renamed_files = Column(Integer, default=0)
    filtered_files = Column(Integer, default=0)
    nas_destination = Column(String(255), nullable=True)  # e.g., "Lharmony/Malayalam Movies"
    detected_category = Column(String(100), nullable=True)  # Auto-detected category
    metadata_found = Column(String(10), default="unknown")  # yes, no, unknown
    plex_scan_status = Column(String(50), nullable=True)  # pending, scanning, completed, failed
    plex_library_name = Column(String(100), nullable=True)  # Library being scanned
    
    # Size information (in bytes)
    input_size = Column(Integer, nullable=True)
    output_size = Column(Integer, nullable=True)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Error information
    error_message = Column(Text, nullable=True)
    error_details = Column(Text, nullable=True)
    
    # Metadata
    user_agent = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    def __repr__(self):
        return f"<Job(id={self.id}, type={self.job_type}, status={self.status})>"
    
    def to_dict(self):
        """Convert job to dictionary"""
        return {
            "id": self.id,
            "job_type": self.job_type.value if self.job_type else None,
            "status": self.status.value if self.status else None,
            "input_path": self.input_path,
            "output_path": self.output_path,
            "filename": self.filename,
            "language": self.language,
            "volume_boost": self.volume_boost,
            "conversion_preset": self.conversion_preset,
            "progress": self.progress,
            "current_file": self.current_file,
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            # Enhanced tracking fields
            "phase": self.phase,
            "renamed_files": self.renamed_files,
            "filtered_files": self.filtered_files,
            "nas_destination": self.nas_destination,
            "detected_category": self.detected_category,
            "metadata_found": self.metadata_found,
            "plex_scan_status": self.plex_scan_status,
            "plex_library_name": self.plex_library_name,
            "input_size": self.input_size,
            "output_size": self.output_size,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration": self._calculate_duration(),
            "error_message": self.error_message,
            "error_details": self.error_details,
        }
    
    def _calculate_duration(self) -> Optional[float]:
        """Calculate job duration in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.utcnow() - self.started_at).total_seconds()
        return None


class DatabaseManager:
    """Database manager for job history"""
    
    def __init__(self, db_path: str = "media_organizer.db"):
        """Initialize database manager"""
        self.db_path = Path(db_path)
        self.engine = create_engine(f"sqlite:///{self.db_path}", echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
        
        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)
        
        # Run migrations for new columns
        self._migrate_schema()
    
    def _migrate_schema(self):
        """Add new columns to existing tables if they don't exist."""
        import sqlite3
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Get existing columns
        cursor.execute("PRAGMA table_info(jobs)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        # New columns to add
        new_columns = [
            ("phase", "VARCHAR(50) DEFAULT 'pending'"),
            ("renamed_files", "INTEGER DEFAULT 0"),
            ("filtered_files", "INTEGER DEFAULT 0"),
            ("nas_destination", "VARCHAR(255)"),
            ("detected_category", "VARCHAR(100)"),
            ("metadata_found", "VARCHAR(10) DEFAULT 'unknown'"),
            ("plex_scan_status", "VARCHAR(50)"),
            ("plex_library_name", "VARCHAR(100)"),
        ]
        
        for col_name, col_type in new_columns:
            if col_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_type}")
                    print(f"Added column: {col_name}")
                except sqlite3.OperationalError:
                    pass  # Column might already exist
        
        conn.commit()
        conn.close()
    
    @contextmanager
    def get_session(self) -> Session:
        """Get database session context manager"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def create_job(
        self,
        job_type: JobType,
        input_path: str,
        output_path: Optional[str] = None,
        filename: Optional[str] = None,
        language: Optional[str] = None,
        volume_boost: Optional[float] = None,
        conversion_preset: Optional[str] = None,
    ) -> Job:
        """Create a new job"""
        with self.get_session() as session:
            job = Job(
                job_type=job_type,
                status=JobStatus.PENDING,
                input_path=input_path,
                output_path=output_path,
                filename=filename,
                language=language,
                volume_boost=volume_boost,
                conversion_preset=conversion_preset,
            )
            session.add(job)
            session.flush()
            session.refresh(job)
            
            # Make sure all attributes are loaded before session closes
            job_id = job.id
            job_status = job.status
            
            return job
    
    def get_job(self, job_id: int) -> Optional[Job]:
        """Get job by ID"""
        with self.get_session() as session:
            return session.query(Job).filter(Job.id == job_id).first()
    
    def update_job_status(
        self,
        job_id: int,
        status: JobStatus,
        error_message: Optional[str] = None,
        error_details: Optional[str] = None,
    ) -> Optional[Job]:
        """Update job status"""
        with self.get_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = status
                
                if status == JobStatus.IN_PROGRESS and not job.started_at:
                    job.started_at = datetime.utcnow()
                elif status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                    job.completed_at = datetime.utcnow()
                
                if error_message:
                    job.error_message = error_message
                if error_details:
                    job.error_details = error_details
                
                session.commit()
                session.refresh(job)
            return job
    
    def update_job_progress(
        self,
        job_id: int,
        progress: float,
        current_file: Optional[str] = None,
        processed_files: Optional[int] = None,
    ) -> Optional[Job]:
        """Update job progress"""
        with self.get_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            if job:
                job.progress = min(100.0, max(0.0, progress))
                if current_file:
                    job.current_file = current_file
                if processed_files is not None:
                    job.processed_files = processed_files
                session.commit()
                session.refresh(job)
            return job
    
    def update_job_phase(
        self,
        job_id: int,
        phase: str,
        nas_destination: Optional[str] = None,
        detected_category: Optional[str] = None,
        renamed_files: Optional[int] = None,
        filtered_files: Optional[int] = None,
        metadata_found: Optional[str] = None,
        plex_scan_status: Optional[str] = None,
        plex_library_name: Optional[str] = None,
    ) -> Optional[Job]:
        """Update job phase and enhanced tracking fields"""
        with self.get_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            if job:
                job.phase = phase
                if nas_destination is not None:
                    job.nas_destination = nas_destination
                if detected_category is not None:
                    job.detected_category = detected_category
                if renamed_files is not None:
                    job.renamed_files = renamed_files
                if filtered_files is not None:
                    job.filtered_files = filtered_files
                if metadata_found is not None:
                    job.metadata_found = metadata_found
                if plex_scan_status is not None:
                    job.plex_scan_status = plex_scan_status
                if plex_library_name is not None:
                    job.plex_library_name = plex_library_name
                session.commit()
                session.refresh(job)
            return job
    
    def get_all_jobs(
        self,
        status: Optional[JobStatus] = None,
        job_type: Optional[JobType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Job]:
        """Get all jobs with optional filtering"""
        with self.get_session() as session:
            query = session.query(Job)
            
            if status:
                query = query.filter(Job.status == status)
            if job_type:
                query = query.filter(Job.job_type == job_type)
            
            query = query.order_by(Job.created_at.desc())
            query = query.limit(limit).offset(offset)
            
            return query.all()
    
    def get_active_jobs(self) -> List[Job]:
        """Get all active (in-progress) jobs"""
        return self.get_all_jobs(status=JobStatus.IN_PROGRESS)
    
    def get_recent_jobs(self, limit: int = 20) -> List[Job]:
        """Get recent jobs"""
        return self.get_all_jobs(limit=limit)
    
    def get_job_stats(self) -> dict:
        """Get job statistics"""
        with self.get_session() as session:
            total = session.query(Job).count()
            completed = session.query(Job).filter(Job.status == JobStatus.COMPLETED).count()
            failed = session.query(Job).filter(Job.status == JobStatus.FAILED).count()
            in_progress = session.query(Job).filter(Job.status == JobStatus.IN_PROGRESS).count()
            
            return {
                "total": total,
                "completed": completed,
                "failed": failed,
                "in_progress": in_progress,
                "pending": total - completed - failed - in_progress,
                "success_rate": (completed / total * 100) if total > 0 else 0,
            }
    
    def delete_old_jobs(self, days: int = 30) -> int:
        """Delete jobs older than specified days"""
        with self.get_session() as session:
            cutoff_date = datetime.utcnow() - datetime.timedelta(days=days)
            deleted = session.query(Job).filter(Job.created_at < cutoff_date).delete()
            session.commit()
            return deleted


# Singleton instance
_db_manager: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    """Get database manager singleton"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


if __name__ == "__main__":
    # Test database
    db = get_db()
    print("✅ Database initialized")
    print(f"📊 Stats: {db.get_job_stats()}")

