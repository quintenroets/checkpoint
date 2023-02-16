from collections import defaultdict

from hypothesis import given, strategies

from checkpoint.checkpoint import CheckpointInfo


class Strategies:
    list_of_strings = strategies.sets(strategies.text(), min_size=1)
    info_keys = strategies.sampled_from(["urls", "commands", "konsole"])
    info_dict = strategies.dictionaries(keys=info_keys, values=list_of_strings)
    checkpoint_info = strategies.builds(
        lambda info_dict: CheckpointInfo.from_dict(info_dict), info_dict
    )


@given(info_dict=Strategies.info_dict)
def test_checkpoint_info_creation(info_dict):
    checkpoint_info = CheckpointInfo.from_dict(info_dict)
    default_info_dict = defaultdict(lambda: set({}), info_dict)
    assert checkpoint_info.urls == default_info_dict["urls"]
    assert checkpoint_info.commands == default_info_dict["commands"]
    assert checkpoint_info.konsole == default_info_dict["konsole"]
    assert checkpoint_info.dict() == info_dict


@given(checkpoint_info=Strategies.checkpoint_info, content=strategies.text())
def test_direct_add_remove(checkpoint_info, content):
    original_dict = checkpoint_info.dict()
    for field in checkpoint_info.fields:
        if content not in field:
            field.add(content)
            assert content in field
            field.remove(content)
            assert checkpoint_info.dict() == original_dict


@given(checkpoint_info=Strategies.checkpoint_info, content=strategies.text())
def test_indirect_add_remove(checkpoint_info: CheckpointInfo, content):
    original_dict = checkpoint_info.dict()
    for field in checkpoint_info.fields:
        if content not in checkpoint_info.get_items():
            field.add(content)
            assert content in field
            checkpoint_info.remove(content)
            assert checkpoint_info.dict() == original_dict
