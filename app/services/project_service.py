from app.database.db_manager import DatabaseManager
from app.database.repositories import ProjectRepository, VideoRepository, RecentFileRepository
from app.models.entities import Project, Video, RecentFile


class ProjectService:
    def __init__(self, db_manager: DatabaseManager):
        self.project_repo = ProjectRepository(db_manager)
        self.video_repo = VideoRepository(db_manager)
        self.recent_repo = RecentFileRepository(db_manager)

    def create_project(self, name: str, file_path: str) -> Project:
        project = Project(name=name, file_path=file_path)
        self.project_repo.save(project)
        # add to recent files
        recent = RecentFile(path=file_path, name=name)
        self.recent_repo.save(recent)
        return project

    def add_video_to_project(self, project: Project, video: Video) -> None:
        # ensure video.project_id is set
        video.project_id = project.id
        self.video_repo.save(video)
