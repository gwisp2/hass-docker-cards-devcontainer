import os
from pathlib import Path
from typing import Dict, List

from rich.markup import escape

from hactl.tasks.task import Task


def make_name_to_path_dict(paths: List[Path]) -> Dict[str, Path]:
    result: Dict[str, Path] = {}
    for path in paths:
        if path.name in result:
            raise RuntimeError(
                f"Two candidates for {path.name}: {path} and {result[path.name]}"
            )
        result[path.name] = path
    return result


def update_symlinks(root_dir: Path, paths: Dict[str, Path], logger: Task) -> List[Path]:
    """
    Creates or updated symlinks in [root_dir] so that they target files
    from [paths]. Any other symlinks in [root_dir] are deleted.
    Returns paths of the created/updated symlinks.
    """

    # Whilelist of symlinks that will not be deleted
    symlink_paths: List[Path] = []

    # Create or update symlinks
    for name, target in paths.items():
        symlink_path = root_dir / name
        symlink_paths.append(symlink_path)

        if symlink_path.is_symlink() and Path(os.readlink(symlink_path)) != target:
            # Update
            symlink_path.unlink()
            symlink_path.symlink_to(target)
            logger.log(f"[yellow](symlink, updated)[/] {escape(str(symlink_path))}")
        elif symlink_path.is_symlink():
            # Do nothing: symlink is correct
            logger.log(f"(symlink, ok) {escape(str(symlink_path))}")
        elif symlink_path.exists():
            # File exists, and it is not a symlink: error
            raise RuntimeError(
                f"Can't create link {symlink_path}:"
                " that file exists and is not a symlink"
            )
        else:
            # Create
            symlink_path.symlink_to(target)
            logger.log(f"(symlink, created) {escape(str(symlink_path))}")

    # Delete any old symlinks
    for name in os.listdir(root_dir):
        file_path = root_dir / name
        if file_path.is_symlink() and file_path not in symlink_paths:
            file_path.unlink()
            logger.log(f"(symlink, removed) {escape(str(file_path))}")

    return symlink_paths
