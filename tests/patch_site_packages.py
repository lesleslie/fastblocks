#!/usr/bin/env python3
import argparse
import re
import shutil
import sys
from pathlib import Path


def find_acb_modules():
    """Find the ACB module and actions module in site-packages."""
    acb_init_path = None
    acb_actions_init_path = None

    for path in sys.path:
        if not path:
            continue

        init_path = Path(path) / "acb" / "__init__.py"
        actions_init_path = Path(path) / "acb" / "actions" / "__init__.py"

        if init_path.exists():
            acb_init_path = init_path

        if actions_init_path.exists():
            acb_actions_init_path = actions_init_path

        if acb_init_path and acb_actions_init_path:
            break

    return acb_init_path, acb_actions_init_path


def backup_file(file_path: Path) -> Path:
    """Create a backup of the specified file."""
    backup_path = file_path.with_suffix(file_path.suffix + ".bak")
    if not backup_path.exists():
        shutil.copy2(file_path, backup_path)
    return backup_path


def restore_from_backup(file_path: Path) -> bool:
    """Restore file from backup."""
    backup_path = file_path.with_suffix(file_path.suffix + ".bak")
    if backup_path.exists():
        shutil.copy2(backup_path, file_path)
        return True
    return False


def patch_acb_init(file_path: Path) -> bool:
    """Patch the ACB __init__.py file to replace register_pkg with a no-op version."""
    content = file_path.read_text()

    # Look for the register_pkg function definition
    register_pkg_pattern = (
        r"def register_pkg\(\) ->\s*None:\n([\s\S]+?)(?=\n\n|\n[^\s]|$)"
    )

    # Create a no-op version that preserves function signature
    replacement = (
        "def register_pkg() -> None:\n    # Patched by FastBlocks tests\n    return"
    )

    if re.search(register_pkg_pattern, content):
        patched_content = re.sub(register_pkg_pattern, replacement, content)
        file_path.write_text(patched_content)
        return True
    return False


def patch_acb_actions(file_path: Path) -> bool:
    """Patch the ACB actions/__init__.py file to replace register_actions with a no-op version."""
    content = file_path.read_text()

    # Look for the register_actions function definition
    register_actions_pattern = r"async def register_actions\(path: AsyncPath\) -> list\[Action\]:\n([\s\S]+?)(?=\n\n|\n[^\s]|$)"

    # Create a simplified version that returns an empty list
    replacement = "async def register_actions(path: AsyncPath) -> list[Action]:\n    # Patched by FastBlocks tests\n    return []"

    if re.search(register_actions_pattern, content):
        patched_content = re.sub(register_actions_pattern, replacement, content)
        file_path.write_text(patched_content)
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Patch ACB module for tests")
    parser.add_argument("--restore", action="store_true", help="Restore from backup")
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    args = parser.parse_args()

    acb_init_path, acb_actions_init_path = find_acb_modules()

    if not acb_init_path:
        return 1

    if not acb_actions_init_path:
        return 1

    if args.verbose:
        pass

    if args.restore:
        success_init = restore_from_backup(acb_init_path)
        success_actions = restore_from_backup(acb_actions_init_path)

        if success_init and success_actions:
            return 0
        return 1
    # Backup and patch both modules
    backup_file(acb_init_path)
    backup_file(acb_actions_init_path)

    success_init = patch_acb_init(acb_init_path)
    success_actions = patch_acb_actions(acb_actions_init_path)

    if success_init and success_actions:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
