import pytest
from pydantic import ValidationError

from venus_protocol.schemas.connections import NodeHello


def test_node_hello_accepts_device_id():
    hello = NodeHello(device_id="laptop-1")

    assert hello.device_id == "laptop-1"


def test_node_hello_rejects_blank_device_id():
    with pytest.raises(ValidationError, match="device_id must not be blank"):
        NodeHello(device_id="   ")


def test_node_hello_rejects_unknown_field():
    with pytest.raises(ValidationError):
        NodeHello(device_id="laptop-1", command="open spotify")
