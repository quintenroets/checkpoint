import os
import sys

from libs.errorhandler import ErrorHandler
from libs.gui import Gui
from libs.cli import Cli
from libs.path import Path

root = Path.assets / "checkpoints"

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
        name = Gui.ask(title, options | extra_options_dict) if options else self.create_path().name
        if not name:
            checkpoint_path = None
        elif name not in extra_options:
            checkpoint_path = root / self.categorie / name
            checkpoint_path.touch(exist_ok=True) # mark as most recent
        else:
            checkpoint_path = name
        
        return checkpoint_path

    def create_path(self):
        name = Gui.ask("Give new checkpoint name")
        if name:
            path = root / self.categorie / name.lower()
            path.save({"urls": [], "commands": []})
        else:
            path = None
        return path



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
                while checkpoint.path is not None and checkpoint != "quit":
                    checkpoint.path = checkpoint.ask_path("Choose checkpoint to remove", "quit")
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
        console_keyword = "__CONSOLE__"
        Cli.run(
            (it.replace(console_keyword, "") for it in checkpoint["commands"] if it.startwith(console_keyword)),
            console=True
        )
        commands = [c for c in checkpoint["commands"] if not c.startswith("__CONSOLE__")]
        commands += [f'xdg-open "{u}"' for u in checkpoint["urls"]]
        Cli.run(commands, wait=False)

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
            new_items = Cli.get(command).split(separator)
            
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
        checkpoints = (root / category).glob("*.yaml")
        checkpoints = sorted(checkpoints, key=lambda path: -path.stat().st_mtime)
        return checkpoints


def main():
    with ErrorHandler():
        args = sys.argv[1:]

        choose = "choose" in args
        if choose:
            args.remove("choose")
        category = args[-1] if args else "Documents"
        CheckpointManager.start(category, choose)


if __name__ == "__main__":
    main()
