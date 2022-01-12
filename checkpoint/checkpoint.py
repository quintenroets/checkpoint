import cli
import os
from plib import Path as BasePath
import sys

from libs.gui import Gui


class Path(BasePath):
    checkpoints = BasePath.assets / "checkpoints"


class Checkpoint:
    def __init__(self, categorie, choose=False):
        self.categorie = categorie
        self.path = None
        if not choose:
            self.path = CheckpointManager.get_recent_path(categorie)
        if self.path is None:
            self.path = self.ask_path("Choose checkpoint", "edit")

    def ask_path(self, title, *extra_options):
        extra_options_dict = {o.capitalize(): o for o in extra_options}
        checkpoint_paths = CheckpointManager.get_checkpoints(self.categorie)
        options = {c.stem.capitalize(): c for c in checkpoint_paths}
        name = Gui.ask(title, options | extra_options_dict) if options else self.create_path()
        if not name:
            checkpoint_path = None
        elif name not in extra_options:
            checkpoint_path = Path.checkpoints / self.categorie / name
            checkpoint_path.touch(exist_ok=True) # mark as most recent
        else:
            checkpoint_path = name
        
        return checkpoint_path

    def create_path(self):
        name = Gui.ask("Give new checkpoint name")
        if name:
            path = Path.checkpoints / self.categorie / name.lower()
            path.save({"urls": [], "commands": []})
        return name


class CheckpointManager:
    @staticmethod
    def start(category, choose=False):
        checkpoint = Checkpoint(category, choose=choose)

        if checkpoint.path == "edit":
            checkpoint.path = checkpoint.ask_path(
                "Choose checkpoint to edit", "create new checkpoint", "remove checkpoint"
            )
            if checkpoint.path == "create new checkpoint":
                checkpoint.path = checkpoint.create_path()
            elif checkpoint.path == "remove checkpoint":
                checkpoint.path = "go"
                while path := checkpoint.ask_path("Choose checkpoint to remove", "quit") not in [None, "quit"]:
                    checkpoint.path.unlink()
                checkpoint.path = None
            else:
                CheckpointManager.edit_checkpoint(checkpoint)

        if checkpoint.path is not None:
            content = checkpoint.path.load()
            if not content["urls"] and not content["commands"]:
                CheckpointManager.edit_checkpoint(checkpoint)
            CheckpointManager.open_checkpoint(content)

    @staticmethod
    def open_checkpoint(checkpoint):
        cli.urlopen(checkpoint["urls"])
        
        console_keyword = "__CONSOLE__"
        for command in checkpoint['commands']:
            if command.startswith(console_keyword):
                cli.run(command.replace(console_keyword, ''), console=True)
            else:
                cli.start(command)

    @staticmethod
    def edit_checkpoint(checkpoint):
        content = checkpoint.path.load()

        item = "Go"
        while item and item != "Quit":
            items = content["urls"] + content["commands"]
            item = Gui.ask("Choose item to remove or add new item", ["Add new"] + items + ["Quit"])
            if item == "Add new":
                CheckpointManager.add_item(content)
            elif item in content["urls"]:
                content["urls"].remove(item)
            elif item in content["commands"]:
                content["commands"].remove(item)
            checkpoint.path.save(content)


    @staticmethod
    def add_item(checkpoint):
        item_type = Gui.ask("Choose item type", ["File", "Folder", "Url", "Command", "Cancel"]).lower()

        if item_type in ["file", "folder"]:
            separator = "###"
            # add / after initdir to force zenity to go into that folder
            option = "--directory" if item_type == "folder" else ""
            initdir = Path.docs
            command = f'zenity --file-selection {option} --filename="{initdir}"/ --multiple --separator={separator}'
            new_items = cli.get(command)
            
            if new_items:
                new_items = new_items.split(separator)
            
            if new_items:
                for item in new_items:
                    if item.endswith(".ipynb"):
                        new_items.remove(item)
                        checkpoint["commands"].append(f"__CONSOLE__cd \"{Path(item).parent}\"; jn")
                checkpoint["urls"] += new_items

        elif item_type in ["url", "command"]:
            item = Gui.ask(f"Give {item_type}")
            if item:
                if item_type == "command" and Gui.ask_yn("Run in console?"):
                    item = "__CONSOLE__" + item
                checkpoint[f"{item_type}s"].append(item)
                
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
    with cli.errorhandler():
        args = sys.argv[1:]

        choose = "choose" in args
        if choose:
            args.remove("choose")
        category = args[-1] if args else "Documents"
        CheckpointManager.start(category, choose)


if __name__ == "__main__":
    main()
