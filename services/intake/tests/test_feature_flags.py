import pytest

from app.schemas.enums import City
from app.services import feature_flags as flags_module


def _document(
    *,
    dispatch_enabled=True,
    cities=None,
):
    return {
        "version": "1",
        "values": {
            "auto_dispatch_enabled": {
                "enabled": dispatch_enabled,
                "enabled_cities": cities or ["PEREIRA", "MANIZALES"],
            }
        },
    }


def test_flags_allow_auto_dispatch_only_for_configured_cities():
    flags = flags_module._parse_flags(_document())

    assert flags.allows_auto_dispatch(City.PEREIRA)
    assert flags.allows_auto_dispatch(City.MANIZALES)
    assert not flags.allows_auto_dispatch(City.CALI)
    assert not flags.allows_auto_dispatch(City.CHOCO)


def test_global_kill_switch_disables_auto_dispatch_for_every_city():
    flags = flags_module._parse_flags(_document(dispatch_enabled=False))

    assert not any(flags.allows_auto_dispatch(city) for city in City)


def test_invalid_city_in_feature_flag_document_is_rejected():
    with pytest.raises(ValueError, match="unsupported city"):
        flags_module._parse_flags(_document(cities=["BOGOTA"]))


def test_local_runtime_uses_safe_defaults_without_calling_aws(monkeypatch):
    monkeypatch.setattr(flags_module, "_is_lambda_runtime", lambda: False)
    store = flags_module.AppConfigFeatureFlagStore()

    assert store.get() == flags_module.SAFE_LOCAL_DEFAULTS
