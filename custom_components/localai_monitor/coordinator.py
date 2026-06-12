"""Data coordinator for the LocalAI Manager integration."""
from asyncio import timeout
from datetime import datetime, timedelta, timezone
import logging
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    BACKEND_STATE_NAMES,
    DOMAIN,
    ENDPOINT_BACKENDS,
    ENDPOINT_BACKEND_MONITOR,
    ENDPOINT_MODELS,
    ENDPOINT_MODELS_JOBS,
    ENDPOINT_MODEL_CONFIG,
    ENDPOINT_SYSTEM,
    ENDPOINT_RESOURCES,
    ENDPOINT_VRAM_ESTIMATE,
    ENDPOINT_VERSION,
    SENSOR_BACKENDS,
    SENSOR_MODELS,
    SENSOR_MODELS_JOBS,
    SENSOR_RUNNING_MODELS,
    SENSOR_SYSTEM,
    SENSOR_RESOURCES,
    SENSOR_VERSION,
)

_LOGGER = logging.getLogger(__name__)


class LocalAIDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching LocalAI data."""

    def __init__(
        self,
        hass: HomeAssistant,
        url: str,
        api_key: str | None,
        verify_ssl: bool,
        scan_interval: int,
    ) -> None:
        """Initialize."""
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.verify_ssl = verify_ssl
        self._hass = hass
        self.last_update_success_time: datetime | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        session = async_get_clientsession(self._hass, verify_ssl=self.verify_ssl)

        try:
            async with timeout(30):
                data = {}
                
                # Fetch backends
                data[SENSOR_BACKENDS] = await self._fetch_endpoint(session, ENDPOINT_BACKENDS)
                
                # Fetch models
                data[SENSOR_MODELS] = await self._fetch_endpoint(session, ENDPOINT_MODELS)
                
                # Fetch model jobs
                data[SENSOR_MODELS_JOBS] = await self._fetch_endpoint(session, ENDPOINT_MODELS_JOBS)
                
                # Fetch system info
                data[SENSOR_SYSTEM] = await self._fetch_endpoint(session, ENDPOINT_SYSTEM)

                # Fetch resources (undocumented)
                data[SENSOR_RESOURCES] = await self._fetch_endpoint(session, ENDPOINT_RESOURCES)

                # Fetch version
                data[SENSOR_VERSION] = await self._fetch_endpoint(session, ENDPOINT_VERSION)

                # Enrich each running (loaded) model with its backend and
                # resource usage. /system only returns the model id, so we
                # query the per-model endpoints to find the backend and VRAM.
                data[SENSOR_RUNNING_MODELS] = await self._build_running_models(
                    session, data[SENSOR_SYSTEM]
                )

                self.last_update_success_time = datetime.now(timezone.utc)
                return data

        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def _fetch_endpoint(self, session, endpoint: str) -> dict[str, Any] | list[Any] | None:
        """Fetch data from a specific endpoint."""
        url = f"{self.url}{endpoint}"
        headers = {}
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with session.get(
                url,
                headers=headers,
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    _LOGGER.warning(
                        "Failed to fetch %s: HTTP %s", endpoint, response.status
                    )
                    return None
        except Exception as err:
            _LOGGER.warning("Error fetching %s: %s", endpoint, err)
            return None

    async def _request_json(
        self,
        session,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any | None:
        """Make a request and return parsed JSON, or None on any failure.

        Used for the per-model enrichment endpoints, which may legitimately
        return non-200 (e.g. /backend/monitor returns 500 for backends that
        don't implement the status RPC). Those are expected, so we log at
        debug level and return None rather than warning.
        """
        url = f"{self.url}{endpoint}"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if json_body is not None:
            headers["Content-Type"] = "application/json"

        try:
            async with session.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json_body,
            ) as response:
                if response.status == 200:
                    return await response.json()
                _LOGGER.debug(
                    "Non-200 from %s %s: HTTP %s", method, endpoint, response.status
                )
                return None
        except Exception as err:  # noqa: BLE001 - best-effort enrichment
            _LOGGER.debug("Error requesting %s %s: %s", method, endpoint, err)
            return None

    async def _build_running_models(
        self, session, system_data: Any
    ) -> list[dict[str, Any]]:
        """Build the enriched list of running models.

        Each entry carries the model id plus, where the server exposes it,
        the backend serving the model and its VRAM usage.
        """
        loaded_models: list[Any] = []
        if isinstance(system_data, dict):
            loaded = system_data.get("loaded_models", [])
            if isinstance(loaded, list):
                loaded_models = loaded

        running: list[dict[str, Any]] = []
        for entry in loaded_models:
            if not isinstance(entry, dict) or not entry.get("id"):
                continue
            model_id = entry["id"]
            info: dict[str, Any] = {"id": model_id}
            info.update(await self._fetch_model_detail(session, model_id))
            running.append(info)

        return running

    async def _fetch_model_detail(
        self, session, model_id: str
    ) -> dict[str, Any]:
        """Fetch backend and resource details for a single loaded model."""
        detail: dict[str, Any] = {}

        # Backend serving the model (from its config).
        config = await self._request_json(
            session, "GET", ENDPOINT_MODEL_CONFIG.format(name=model_id)
        )
        if isinstance(config, dict):
            detail["backend"] = config.get("backend") or "auto"

        # VRAM estimate for the model. This is an estimate from the model
        # config, not measured usage, but it is the only per-model VRAM figure
        # LocalAI exposes for most backends.
        estimate = await self._request_json(
            session,
            "POST",
            ENDPOINT_VRAM_ESTIMATE,
            json_body={"model": model_id},
        )
        if isinstance(estimate, dict):
            vram_bytes = estimate.get("vram_bytes")
            if isinstance(vram_bytes, (int, float)):
                detail["vram_estimate_bytes"] = vram_bytes
                detail["vram_estimate_gb"] = round(vram_bytes / (1024**3), 2)
            if estimate.get("vram_display"):
                detail["vram_estimate_display"] = estimate["vram_display"]
            if isinstance(estimate.get("context_length"), int):
                detail["context_length"] = estimate["context_length"]

        # Best-effort live status/memory from the backend process. Returns
        # non-200 for backends that don't implement the status RPC, in which
        # case these keys are simply absent.
        monitor = await self._request_json(
            session,
            "GET",
            ENDPOINT_BACKEND_MONITOR,
            params={"model": model_id},
        )
        if isinstance(monitor, dict) and "error" not in monitor:
            state = monitor.get("state")
            if isinstance(state, int):
                detail["state"] = BACKEND_STATE_NAMES.get(state, str(state))
            memory = monitor.get("memory")
            if isinstance(memory, dict) and isinstance(
                memory.get("total"), (int, float)
            ):
                detail["memory_bytes"] = memory["total"]
                detail["memory_gb"] = round(memory["total"] / (1024**3), 2)

        return detail


