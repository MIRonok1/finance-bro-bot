from types import SimpleNamespace

from app.handlers.filters import not_a_command


def _message(text):
    return SimpleNamespace(text=text)


def test_not_a_command_true_for_plain_text():
    assert not_a_command(_message("42")) is True
    assert not_a_command(_message("1,5")) is True


def test_not_a_command_false_for_slash_commands():
    assert not_a_command(_message("/stats")) is False
    assert not_a_command(_message("/subscribe")) is False


def test_not_a_command_true_for_missing_text():
    # Стикер/фото и т.п. — message.text is None, не должно ломаться и не
    # должно расцениваться как команда.
    assert not_a_command(_message(None)) is True
