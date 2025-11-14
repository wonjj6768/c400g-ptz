# tests/test_basic.py
# TODO: Add tests later

def test_import():
    """Test that the package can be imported."""
    from c400g_ptz import C400GPTZ, __version__
    assert C400GPTZ is not None
    assert __version__ is not None
