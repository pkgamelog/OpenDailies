from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict
import uuid

def generate_uuid() -> str:
    return str(uuid.uuid4())

@dataclass
class BaseEntity:
    id: str = field(default_factory=generate_uuid)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class Project(BaseEntity):
    name: str = "Untitled Project"
    file_path: str = ""
    last_opened_video_id: Optional[str] = None

@dataclass
class Video(BaseEntity):
    project_id: str = ""
    file_path: str = ""
    file_name: str = ""
    duration_ms: int = 0
    frame_rate: float = 24.0
    width: int = 0
    height: int = 0
    codec: str = ""

@dataclass
class Comment(BaseEntity):
    video_id: str = ""
    frame_number: int = 0
    timecode_ms: int = 0
    author: str = "Anonymous"
    text: str = ""
    color_tag: str = "#FFFFFF"
    is_resolved: bool = False
    parent_id: Optional[str] = None

@dataclass
class Annotation(BaseEntity):
    video_id: str = ""
    frame_number: int = 0
    duration_frames: int = 1  
    author: str = ""
    data: Dict = field(default_factory=dict)
    color: str = "#FF0000"


@dataclass
class Bookmark(BaseEntity):
    video_id: str = ""
    frame_number: int = 0
    name: str = ""
    color: str = "#00FF00"


@dataclass
class Settings(BaseEntity):
    recent_projects_limit: int = 10
    theme: str = "light"
    auto_save_interval_sec: int = 60


@dataclass
class RecentFile(BaseEntity):
    path: str = ""
    name: str = ""
    last_opened_at: str = field(default_factory=lambda: datetime.now().isoformat())

