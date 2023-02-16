import sys
from dataclasses import asdict, dataclass, field

import cli
import gui
from plib import Path as BasePath


class Path(BasePath):
    @classmethod
    @property
    def checkpoints(cls):
        return cls.assets / "checkpoints"


@dataclass
class CheckpointInfo:
    urls: set[str] = field(default_factory=set)
    commands: set[str] = field(default_factory=set)
    konsole: set[str] = field(default_factory=set)

    @classmethod
    def from_dict(cls, info):
        return CheckpointInfo(**info)

    def dict(self):
        info = asdict(self)
        info_pruned = {k: v for k, v in info.items() if v}
        return info_pruned

    def get_items(self):
        return [item for items in asdict(self).values() for item in items]

    @property
    def fields(self):
        return self.urls, self.commands, self.konsole

    def remove(self, item):
        for field_instance in self.fields:
            if item in field_instance:
                field_instance.remove(item)


class Checkpoint:
    def __init__(self, category, choose=False):
        self.category = category
        self.title = category.replace("_", " ")
        self.path = None
        if not choose:
            self.path = CheckpointManager.get_recent_path(category)
        if self.path is None:
            self.path = self.ask_path("Choose checkpoint", "edit")

    def ask(self, message, choices=None, options=None):
        options = options or {}
        options["title"] = self.title
        return gui.ask(message, choices=choices, options=options)

    def ask_path(self, title, *extra_options):
        extra_options_dict = {o.capitalize(): o for o in extra_options}
        checkpoint_paths = CheckpointManager.get_checkpoints(self.category)
        options = {c.stem.capitalize(): c for c in checkpoint_paths}

        if not options:
            checkpoint_path = self.create_path()
        else:
            name = self.ask(title, options | extra_options_dict)
            if not name:
                checkpoint_path = None
            elif name not in extra_options:
                checkpoint_path = (Path.checkpoints / self.category / name).with_suffix(
                    ".yaml"
                )
                checkpoint_path.touch(exist_ok=True)  # mark as most recent
            else:
                checkpoint_path = name

        return checkpoint_path

    @property
    def info(self):
        return CheckpointInfo.from_dict(self.path.yaml)

    @info.setter
    def info(self, checkpoint_info: CheckpointInfo):
        self.path.yaml = checkpoint_info.dict()

    def create_path(self):
        name = self.ask("Give new checkpoint name")
        if name:
            path = (Path.checkpoints / self.category / name.lower()).with_suffix(
                ".yaml"
            )
            path.touch(exist_ok=True)
        else:
            path = None
        return path


class CheckpointManager:
    @staticmethod
    def start(category, choose=False):
        checkpoint = Checkpoint(category, choose=choose)

        if checkpoint.path == "edit":
            checkpoint.path = checkpoint.ask_path(
                "Choose checkpoint to edit",
                "create new checkpoint",
                "remove checkpoint",
            )
            if checkpoint.path == "create new checkpoint":
                checkpoint.path = checkpoint.create_path()
            elif checkpoint.path == "remove checkpoint":
                while (
                    path := checkpoint.ask_path("Choose checkpoint to remove", "quit")
                ) not in (None, "quit"):
                    path.unlink()
                checkpoint.path = None
            else:
                CheckpointManager.edit_checkpoint(checkpoint)

        if checkpoint.path is not None:
            if not checkpoint.info.get_items():
                CheckpointManager.edit_checkpoint(checkpoint)
            CheckpointManager.open_checkpoint(checkpoint.info)

    @staticmethod
    def open_checkpoint(checkpoint: CheckpointInfo):
        cli.urlopen(*checkpoint.urls)
        for command in checkpoint.commands:
            cli.start(command)
        for command in checkpoint.konsole:
            cli.run(command, console=True)

    @staticmethod
    def edit_checkpoint(checkpoint: Checkpoint):
        if checkpoint.path is None:
            return

        checkpoint_info = CheckpointInfo.from_dict(checkpoint.path.yaml)

        item = "Go"
        while item and item != "Quit":
            items = checkpoint_info.get_items()
            options = ["Add new", *items, "Quit"]
            item = checkpoint.ask("Choose item to remove or add new item", options)
            if item == "Add new":
                CheckpointManager.add_item(checkpoint_info)
            else:
                checkpoint_info.remove(item)
            checkpoint.path.yaml = checkpoint_info.dict()

    @staticmethod
    def add_item(checkpoint: CheckpointInfo):
        item_types = ("File", "Folder", "Url", "Command", "Cancel")
        item_type = gui.ask("Choose item type", item_types).lower()

        if item_type in ["file", "folder"]:
            separator = "###"

            options = {
                "file-selection",
                "multiple",
                # add / after init dir to force zenity to go into that folder
                f'filename="{Path.docs}/"',
                f"separator={separator}",
            }
            if item_type == "folder":
                options.add("directory")

            new_items = cli.get("zenity", options)

            if new_items:
                new_items = new_items.split(separator)
                checkpoint.urls.update(new_items)

        elif item_type in ["url", "command"]:
            item = gui.ask(f"Give {item_type}")
            if item:
                match item_type:
                    case "command":
                        if gui.ask_yn("Run in console?"):
                            checkpoint.konsole.add(item)
                        else:
                            checkpoint.commands.add(item)
                    case "url":
                        checkpoint.urls.add(item)

    @staticmethod
    def get_recent_path(category):
        checkpoints = CheckpointManager.get_checkpoints(category)
        checkpoint = checkpoints[0] if checkpoints else None
        return checkpoint

    @staticmethod
    def get_checkpoints(category):
        checkpoints = (Path.checkpoints / category).glob("*.yaml")
        checkpoints = sorted(checkpoints, key=lambda path: -path.mtime)
        return checkpoints


def main():
    args = sys.argv[1:]

    choose = "choose" in args
    if choose:
        args.remove("choose")
    category = args[-1] if args else "Documents"
    CheckpointManager.start(category, choose)


if __name__ == "__main__":
    main()
