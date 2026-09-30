import pytest
from pydantic import ValidationError

from venus_protocol.schemas.connections import NodeApp, NodeHello


def test_node_hello_accepts_device_id():
    hello = NodeHello(device_id="laptop-1")

    assert hello.device_id == "laptop-1"


def test_node_hello_rejects_blank_device_id():
    with pytest.raises(ValidationError, match="device_id must not be blank"):
        NodeHello(device_id="   ")


def test_node_hello_rejects_unknown_field():
    with pytest.raises(ValidationError):
        NodeHello(device_id="laptop-1", command="open spotify")


def test_node_hello_accepts_apps():
    hello = NodeHello(
        device_id="laptop-1",
        apps=[NodeApp(name="Notepad", app_id="Microsoft.WindowsNotepad_8wekyb3d8bbwe!App")],
    )

    assert hello.apps[0].app_id == "Microsoft.WindowsNotepad_8wekyb3d8bbwe!App"


def test_node_hello_defaults_to_no_apps():
    hello = NodeHello(device_id="laptop-1")

    assert hello.apps == []


def test_node_hello_defaults_to_no_projects():
    hello = NodeHello(device_id="laptop-1")

    assert hello.projects == []
