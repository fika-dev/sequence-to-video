import shutil
from datetime import datetime
from pathlib import Path


class FileManager:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_project_dir(self, project_id: str) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_dir = self.base_dir / f"{project_id}_{timestamp}"
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    def copy_to_review(self, source: Path, project_id: str) -> Path:
        review_dir = self.base_dir / "review" / project_id
        review_dir.mkdir(parents=True, exist_ok=True)
        dest = review_dir / source.name
        shutil.copy2(source, dest)
        return dest

    def list_generated(self, project_id: str | None = None) -> list[Path]:
        if project_id:
            pattern = f"{project_id}*"
            return list(self.base_dir.glob(pattern))
        return list(self.base_dir.iterdir())

    def cleanup_temp(self, project_id: str) -> None:
        temp_dirs = list(self.base_dir.glob(f"{project_id}_temp_*"))
        for temp_dir in temp_dirs:
            if temp_dir.is_dir():
                shutil.rmtree(temp_dir)
