import re

import rocototop


def test_version_semver():
    """Verify that the version follows PEP 440 / SemVer patterns."""
    version = rocototop.__version__

    # Standard PEP 440 version (which rocototop uses via setuptools-scm)
    pep440_pattern = r"^(\d+)\.(\d+)\.(\d+)(?:\.dev\d+)?(?:\+g[a-f0-9]+(?:\.d\d+)?)?$"

    assert re.match(pep440_pattern, version), f"Version {version} does not match PEP 440 pattern"


def test_version_tuple():
    """Verify the version_tuple structure."""
    assert hasattr(rocototop, "version_tuple")
    assert isinstance(rocototop.version_tuple, tuple)
    assert len(rocototop.version_tuple) >= 3
    assert isinstance(rocototop.version_tuple[0], int)
    assert isinstance(rocototop.version_tuple[1], int)
    assert isinstance(rocototop.version_tuple[2], int)
