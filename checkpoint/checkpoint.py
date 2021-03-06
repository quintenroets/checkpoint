import collections
import sys

import cli
import gui
from plib import Path as BasePath


class Path(BasePath):
    def load(self, trusted=False):
        content = super().load(trusted=trusted)
        content = collections.defaultdict(lambda: [], content)
        return content

    def save(self, content):
        return super().save(dict(content))

    @classmethod
    @property
    def checkpoints(cls):
        return cls.assets / "checkpoints"


class Checkpoint:
    def __init__(self, categorie, choose=False):
        self.categorie = categorie
        self.title = categorie.replace("_", " ")
        self.path = None
        if not choose:
            self.path = CheckpointManager.get_recent_path(categorie)
        if self.path is None:
            self.path = self.ask_path("Choose checkpoint", "edit")

    def ask(self, message, choices=None, options=None):
        options = options or {}
        options["title"] = self.title
        return gui.ask(message, choices=choices, options=options)

    def ask_path(self, title, *extra_options):
        extra_options_dict = {o.capitalize(): o for o in extra_options}
        checkpoint_paths = CheckpointManager.get_checkpoints(self.categorie)
        options = {c.stem.capitalize(): c for c in checkpoint_paths}

        if not options:
            checkpoint_path = self.create_path()
        else:
            name = self.ask(title, options | extra_options_dict)
            if not name:
                checkpoint_path = None
            elif name not in extra_options:
                checkpoint_path = (
                    Path.checkpoints / self.categorie / name
                ).with_suffix(".yaml")
                checkpoint_path.touch(exist_ok=True)  # mark as most recent
            else:
                checkpoint_path = name

        return checkpoint_path

    def create_path(self):
        name = self.ask("Give new checkpoint name")
        if name:
            path = (Path.checkpoints / self.categorie / name.lower()).with_suffix(
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
                ) not in [None, "quit"]:
                    path.unlink()
                checkpoint.path = None
            else:
                CheckpointManager.edit_checkpoint(checkpoint)

        if checkpoint.path is not None:
            content = checkpoint.path.load()
            if not any([v for v in content.values()]):
                CheckpointManager.edit_checkpoint(checkpoint)
            CheckpointManager.open_checkpoint(content)

    @staticmethod
    def open_checkpoint(checkpoint):
        cli.urlopen(*checkpoint["urls"])

        for command in checkpoint["commands"]:
            cli.start(command)
        for command in checkpoint["konsole"]:
            cli.run(command, console=True)

    @staticmethod
    def edit_checkpoint(checkpoint: Checkpoint):
        if checkpoint.path is None:
            return

        content = checkpoint.path.load()

        item = "Go"
        while item and item != "Quit":
            values = [v for values in content.values() for v in values]
            item = checkpoint.ask(
                "Choose item to remove or add new item", ["Add new"] + values + ["Quit"]
            )
            if item == "Add new":
                CheckpointManager.add_item(content)
            else:
                for k, v in content.items():
                    if item in v:
                        v.remove(item)
            checkpoint.path.save(content)

    @staticmethod
    def add_item(checkpoint):
        item_type = gui.ask(
            "Choose item type", ["File", "Folder", "Url", "Command", "Cancel"]
        ).lower()

        if item_type in ["file", "folder"]:
            separator = "###"

            options = {
                "file-selection",
                "multiple",
                f'filename="{Path.docs}/"',  # add / after initdir to force zenity to go into that folder
                f"separator={separator}",
            }
            if item_type == "folder":
                options.add("directory")

            new_items = cli.get(f"zenity", options)

            if new_items:
                new_items = new_items.split(separator)
                checkpoint["urls"] += new_items

        elif item_type in ["url", "command"]:
            item = gui.ask(f"Give {item_type}")
            if item:
                store_key = (
                    "konsole"
                    if item_type == "command" and gui.ask_yn("Run in console?")
                    else f"{item_type}s"
                )
                checkpoint[store_key].append(item)

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
