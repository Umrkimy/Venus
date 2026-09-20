import venus_node.cli.dev_connect as cli_dev_connect
import venus_node.cli.dev_run as cli_dev_run
import venus_node.dev_connect as dev_connect
import venus_node.dev_run as dev_run


def test_legacy_dev_connect_module_uses_relocated_main():
    assert dev_connect.main is cli_dev_connect.main


def test_legacy_dev_run_module_uses_relocated_main():
    assert dev_run.main is cli_dev_run.main
