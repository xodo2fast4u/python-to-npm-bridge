def test_import_dayjs(runtime_with_packages):
    dayjs = runtime_with_packages.import_module("dayjs")
    assert dayjs is not None


def test_import_dayjs_call(runtime_with_packages):
    dayjs = runtime_with_packages.import_module("dayjs")
    d = dayjs("2026-01-01")
    assert d.format("YYYY-MM-DD") == "2026-01-01"


def test_import_dayjs_today(runtime_with_packages):
    dayjs = runtime_with_packages.import_module("dayjs")
    d = dayjs()
    year = int(d.format("YYYY"))
    assert 2024 <= year <= 2030


def test_import_uuid(runtime_with_packages):
    uuid_mod = runtime_with_packages.import_module("uuid")
    v4 = uuid_mod.v4()
    assert isinstance(v4, str)
    assert len(v4) == 36
