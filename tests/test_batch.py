def test_batch_multiple_requires(runtime_with_packages):
    with runtime_with_packages.batch() as b:
        b.require("lodash")
        b.require("uuid")
    assert len(b.results) == 2
    assert b.results[0] is not None
    assert b.results[1] is not None
