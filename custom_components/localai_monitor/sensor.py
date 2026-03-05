"""Sensor platform for LocalAI Monitor integration."""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_LAST_UPDATE,
    DOMAIN,
    SENSOR_BACKENDS,
    SENSOR_MODELS,
    SENSOR_MODELS_JOBS,
    SENSOR_RESOURCES,
    SENSOR_RUNNING_MODELS,
    SENSOR_SYSTEM,
)
from .coordinator import LocalAIDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LocalAI sensor platform."""
    coordinator: LocalAIDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        LocalAIBackendsSensor(coordinator, entry),
        LocalAIModelsSensor(coordinator, entry),
        LocalAIModelsJobsSensor(coordinator, entry),
        LocalAIRunningModelsSensor(coordinator, entry),
        LocalAISystemSensor(coordinator, entry),
        LocalAIResourcesSensor(coordinator, entry),
    ]

    async_add_entities(entities)


class LocalAISensorBase(CoordinatorEntity, SensorEntity):
    """Base class for LocalAI sensors."""

    def __init__(
        self,
        coordinator: LocalAIDataUpdateCoordinator,
        entry: ConfigEntry,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._sensor_type = sensor_type
        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"
        self._attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer="LocalAI",
            model="LocalAI Server",
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        last_update = getattr(self.coordinator, "last_update_success_time", None)
        attrs = {
            ATTR_LAST_UPDATE: last_update.isoformat() if last_update is not None else None,
        }
        
        # Add sensor-specific attributes (implemented in subclasses)
        return attrs


class LocalAIBackendsSensor(LocalAISensorBase):
    """Sensor for LocalAI backends."""

    def __init__(
        self,
        coordinator: LocalAIDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_BACKENDS)
        self._attr_name = "Installed Backends"
        self._attr_icon = "mdi:library-shelves"

    @property
    def native_value(self) -> int | str:
        """Return the state of the sensor."""
        if not self.coordinator.data or SENSOR_BACKENDS not in self.coordinator.data:
            return "unknown"
        
        data = self.coordinator.data[SENSOR_BACKENDS]
        if data is None:
            return "unavailable"
        
        if isinstance(data, list):
            return len(data)
        
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = super().extra_state_attributes
        
        if not self.coordinator.data or SENSOR_BACKENDS not in self.coordinator.data:
            return attrs
        
        data = self.coordinator.data[SENSOR_BACKENDS]
        if data is None or not isinstance(data, list):
            return attrs
        
        # Extract backend names and metadata
        backend_list = []
        for backend in data:
            if isinstance(backend, dict):
                backend_info = {
                    "name": backend.get("Name", "unknown"),
                }
                if "Metadata" in backend and isinstance(backend["Metadata"], dict):
                    backend_info["alias"] = backend["Metadata"].get("alias")
                    backend_info["installed_at"] = backend["Metadata"].get("installed_at")
                backend_list.append(backend_info)
        
        attrs["backends"] = backend_list
        attrs["backend_names"] = [b["name"] for b in backend_list]
        
        return attrs


class LocalAIModelsSensor(LocalAISensorBase):
    """Sensor for LocalAI models."""

    def __init__(
        self,
        coordinator: LocalAIDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_MODELS)
        self._attr_name = "Installed Models"
        self._attr_icon = "mdi:brain"

    @property
    def native_value(self) -> int | str:
        """Return the state of the sensor."""
        if not self.coordinator.data or SENSOR_MODELS not in self.coordinator.data:
            return "unknown"
        
        data = self.coordinator.data[SENSOR_MODELS]
        if data is None:
            return "unavailable"
        
        if isinstance(data, dict):
            # OpenAI-style response with "data" key
            if "data" in data and isinstance(data["data"], list):
                return len(data["data"])
        
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = super().extra_state_attributes
        
        if not self.coordinator.data or SENSOR_MODELS not in self.coordinator.data:
            return attrs
        
        data = self.coordinator.data[SENSOR_MODELS]
        if data is None:
            return attrs
        
        # Extract model IDs from OpenAI-style response
        model_list = []
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
            model_ids = [model.get("id", "unknown") for model in data["data"] if isinstance(model, dict)]
            
            # Get enriched model details from HTML parsing
            model_details = self.coordinator.data.get("model_details", {})
            
            # Build enriched model list
            for model_id in model_ids:
                model_info = {"id": model_id}
                
                # Add details from HTML if available
                if model_id in model_details:
                    details = model_details[model_id]
                    model_info["backend"] = details.get("backend", "unknown")
                    model_info["status"] = details.get("status", "unknown")
                    model_info["usecases"] = details.get("usecases", [])
                    model_info["mcp_enabled"] = details.get("mcp_enabled", False)
                
                model_list.append(model_info)
            
            attrs["models"] = model_list
            attrs["model_ids"] = model_ids
        
        return attrs


class LocalAIModelsJobsSensor(LocalAISensorBase):
    """Sensor for LocalAI model jobs."""

    def __init__(
        self,
        coordinator: LocalAIDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_MODELS_JOBS)
        self._attr_name = "Model Jobs"
        self._attr_icon = "mdi:briefcase-clock"

    @property
    def native_value(self) -> int | str:
        """Return the state of the sensor."""
        if not self.coordinator.data or SENSOR_MODELS_JOBS not in self.coordinator.data:
            return "unknown"
        
        data = self.coordinator.data[SENSOR_MODELS_JOBS]
        if data is None:
            return "unavailable"
        
        if isinstance(data, list):
            return len(data)
        elif isinstance(data, dict):
            if "jobs" in data and isinstance(data["jobs"], list):
                return len(data["jobs"])
        
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = super().extra_state_attributes
        
        if not self.coordinator.data or SENSOR_MODELS_JOBS not in self.coordinator.data:
            return attrs
        
        data = self.coordinator.data[SENSOR_MODELS_JOBS]
        if data is None:
            return attrs
        
        # Extract job details
        jobs_list = []
        if isinstance(data, list):
            jobs_list = data
        elif isinstance(data, dict) and "jobs" in data and isinstance(data["jobs"], list):
            jobs_list = data["jobs"]
        
        if jobs_list:
            attrs["jobs"] = jobs_list
        
        return attrs


class LocalAIRunningModelsSensor(LocalAISensorBase):
    """Sensor for LocalAI running models."""

    def __init__(
        self,
        coordinator: LocalAIDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_RUNNING_MODELS)
        self._attr_name = "Running Models"
        self._attr_icon = "mdi:brain"

    @property
    def native_value(self) -> int:
        """Return the number of running models."""
        model_details = (self.coordinator.data or {}).get("model_details", {})
        return sum(
            1
            for details in model_details.values()
            if isinstance(details, dict) and details.get("status") == "Running"
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = super().extra_state_attributes

        model_details = (self.coordinator.data or {}).get("model_details", {})
        running = [
            {"name": name, "backend": details.get("backend", "unknown")}
            for name, details in model_details.items()
            if isinstance(details, dict) and details.get("status") == "Running"
        ]
        attrs["running_models"] = running

        return attrs


class LocalAISystemSensor(LocalAISensorBase):
    """Sensor for LocalAI system information."""

    def __init__(
        self,
        coordinator: LocalAIDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_SYSTEM)
        self._attr_name = "System"
        self._attr_icon = "mdi:information"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        if not self.coordinator.data or SENSOR_SYSTEM not in self.coordinator.data:
            return "unknown"
        
        data = self.coordinator.data[SENSOR_SYSTEM]
        if data is None:
            return "unavailable"
        
        if isinstance(data, dict):
            # Try to get version or status
            if "version" in data:
                return str(data["version"])
            if "status" in data:
                return str(data["status"])
        
        return "online"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes with full system information."""
        attrs = super().extra_state_attributes

        if not self.coordinator.data or SENSOR_SYSTEM not in self.coordinator.data:
            return attrs

        data = self.coordinator.data[SENSOR_SYSTEM]
        if data is None:
            return attrs

        if isinstance(data, dict):
            # Expose all system data as attributes
            attrs.update(data)

        return attrs


class LocalAIResourcesSensor(LocalAISensorBase):
    """Sensor for LocalAI resources (undocumented endpoint)."""

    def __init__(
        self,
        coordinator: LocalAIDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_RESOURCES)
        self._attr_name = "Resources"
        self._attr_icon = "mdi:gauge"
        self._attr_native_unit_of_measurement = "%"
        self._attr_suggested_display_precision = 2

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if not self.coordinator.data or SENSOR_RESOURCES not in self.coordinator.data:
            return None
        
        data = self.coordinator.data[SENSOR_RESOURCES]
        if data is None:
            return None
        
        if isinstance(data, dict):
            # Check if available
            if not data.get("available", False):
                return None
            
            # Get usage percent from aggregate
            if "aggregate" in data and isinstance(data["aggregate"], dict):
                usage = data["aggregate"].get("usage_percent")
                if usage is not None:
                    return round(float(usage), 2)
        
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False
        if not self.coordinator.data:
            return False
        data = self.coordinator.data.get(SENSOR_RESOURCES)
        return data is not None and isinstance(data, dict)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = super().extra_state_attributes
        
        if not self.coordinator.data or SENSOR_RESOURCES not in self.coordinator.data:
            return attrs
        
        data = self.coordinator.data[SENSOR_RESOURCES]
        if data is None or not isinstance(data, dict):
            return attrs
        
        # Add aggregate information
        if "aggregate" in data and isinstance(data["aggregate"], dict):
            agg = data["aggregate"]
            attrs["total_memory"] = agg.get("total_memory")
            attrs["used_memory"] = agg.get("used_memory")
            attrs["free_memory"] = agg.get("free_memory")
            attrs["usage_percent"] = agg.get("usage_percent")
            attrs["gpu_count"] = agg.get("gpu_count")
            
            # Format memory in GB for easier reading
            total_memory = attrs.get("total_memory")
            used_memory = attrs.get("used_memory")
            free_memory = attrs.get("free_memory")
            
            if isinstance(total_memory, (int, float)) and total_memory != 0:
                attrs["total_memory_gb"] = round(total_memory / (1024**3), 2)
            if isinstance(used_memory, (int, float)):
                attrs["used_memory_gb"] = round(used_memory / (1024**3), 2)
            if isinstance(free_memory, (int, float)):
                attrs["free_memory_gb"] = round(free_memory / (1024**3), 2)
        
        # Add GPU information
        if "gpus" in data and isinstance(data["gpus"], list):
            gpu_list = []
            for gpu in data["gpus"]:
                if isinstance(gpu, dict):
                    total_vram = gpu.get("total_vram")
                    used_vram = gpu.get("used_vram")
                    free_vram = gpu.get("free_vram")
                    
                    gpu_info = {
                        "index": gpu.get("index"),
                        "name": gpu.get("name"),
                        "vendor": gpu.get("vendor"),
                        "usage_percent": gpu.get("usage_percent"),
                        "total_vram_gb": round(total_vram / (1024**3), 2)
                        if isinstance(total_vram, (int, float)) and total_vram != 0
                        else None,
                        "used_vram_gb": round(used_vram / (1024**3), 2)
                        if isinstance(used_vram, (int, float))
                        else None,
                        "free_vram_gb": round(free_vram / (1024**3), 2)
                        if isinstance(free_vram, (int, float))
                        else None,
                    }
                    gpu_list.append(gpu_info)
            attrs["gpus"] = gpu_list
        
        # Add other resource info
        attrs["resource_type"] = data.get("type")
        attrs["reclaimer_enabled"] = data.get("reclaimer_enabled")
        attrs["reclaimer_threshold"] = data.get("reclaimer_threshold")
        attrs["watchdog_interval"] = data.get("watchdog_interval")
        
        return attrs
