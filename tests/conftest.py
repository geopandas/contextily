def pytest_configure(config):
    config.addinivalue_line("markers",
                            "network: mark tests that use the network.")
