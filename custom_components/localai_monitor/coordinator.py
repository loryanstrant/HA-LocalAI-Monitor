"""Data coordinator for the LocalAI Manager integration."""
from datetime import timedelta
from html.parser import HTMLParser
import logging
from typing import Any

import aiohttp
import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DOMAIN,
    ENDPOINT_BACKENDS,
    ENDPOINT_MODELS,
    ENDPOINT_MODELS_JOBS,
    ENDPOINT_SYSTEM,
    ENDPOINT_RESOURCES,
    SENSOR_BACKENDS,
    SENSOR_MODELS,
    SENSOR_MODELS_JOBS,
    SENSOR_SYSTEM,
    SENSOR_RESOURCES,
)

_LOGGER = logging.getLogger(__name__)


class ModelTableParser(HTMLParser):
    """Parse the /manage page HTML to extract model details."""
    
    def __init__(self):
        """Initialize the parser."""
        super().__init__()
        self.in_tbody = False
        self.in_td = False
        self.current_col = 0
        self.current_row = {'name': '', 'status': [], 'backend': '', 'usecases': []}
        self.models = []
        
    def handle_starttag(self, tag, attrs):
        """Handle opening tags."""
        if tag == 'tbody':
            self.in_tbody = True
        elif tag == 'tr' and self.in_tbody:
            self.current_col = 0
            self.current_row = {'name': '', 'status': [], 'backend': '', 'usecases': []}
        elif tag == 'td' and self.in_tbody:
            self.in_td = True
            
    def handle_endtag(self, tag):
        """Handle closing tags."""
        if tag == 'tbody':
            self.in_tbody = False
        elif tag == 'td':
            self.in_td = False
            self.current_col += 1
        elif tag == 'tr' and self.in_tbody and self.current_row['name']:
            self.models.append(self.current_row.copy())
            
    def handle_data(self, data):
        """Handle text data within tags."""
        if self.in_td:
            data = data.strip()
            if not data:
                return
                
            # Column 0: Name
            if self.current_col == 0 and not self.current_row['name']:
                self.current_row['name'] = data
            # Column 1: Status (Running, MCP, etc.)
            elif self.current_col == 1:
                self.current_row['status'].append(data)
            # Column 2: Backend
            elif self.current_col == 2 and not self.current_row['backend']:
                self.current_row['backend'] = data
            # Column 3: Use Cases
            elif self.current_col == 3:
                self.current_row['usecases'].append(data)


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
        self.session = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        if self.session is None:
            self.session = aiohttp.ClientSession()

        try:
            async with async_timeout.timeout(30):
                data = {}
                
                # Fetch backends
                data[SENSOR_BACKENDS] = await self._fetch_endpoint(ENDPOINT_BACKENDS)
                
                # Fetch models
                data[SENSOR_MODELS] = await self._fetch_endpoint(ENDPOINT_MODELS)
                
                # Fetch model jobs
                data[SENSOR_MODELS_JOBS] = await self._fetch_endpoint(ENDPOINT_MODELS_JOBS)
                
                # Fetch system info
                data[SENSOR_SYSTEM] = await self._fetch_endpoint(ENDPOINT_SYSTEM)
                
                # Fetch resources (undocumented)
                data[SENSOR_RESOURCES] = await self._fetch_endpoint(ENDPOINT_RESOURCES)
                
                # Parse model details from /manage page HTML
                model_details = await self._fetch_model_details()
                if model_details:
                    data["model_details"] = model_details
                
                return data

        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def _fetch_endpoint(self, endpoint: str) -> dict[str, Any] | list[Any] | None:
        """Fetch data from a specific endpoint."""
        url = f"{self.url}{endpoint}"
        headers = {}
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with self.session.get(
                url,
                headers=headers,
                ssl=self.verify_ssl,
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    _LOGGER.warning(
                        "Failed to fetch %s: HTTP %s", endpoint, response.status
                    )
                    return None
        except aiohttp.ClientError as err:
            _LOGGER.warning("Error fetching %s: %s", endpoint, err)
            return None
        except Exception as err:
            _LOGGER.warning("Unexpected error fetching %s: %s", endpoint, err)
            return None

    async def _fetch_model_details(self) -> dict[str, dict[str, Any]] | None:
        """Fetch and parse model details from /manage page HTML."""
        url = f"{self.url}/manage"
        headers = {"Accept": "text/html"}
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with self.session.get(
                url,
                headers=headers,
                ssl=self.verify_ssl,
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    parser = ModelTableParser()
                    parser.feed(html)
                    
                    # Convert list to dict keyed by model name
                    model_dict = {}
                    for model in parser.models:
                        model_dict[model['name']] = {
                            'backend': model['backend'],
                            'status': 'Running' if 'Running' in model['status'] else 'Idle',
                            'usecases': model['usecases'],
                            'mcp_enabled': 'MCP' in model['status'],
                        }
                    
                    _LOGGER.info(
                        "Parsed %d models from /manage page (first 3: %s)",
                        len(model_dict),
                        list(model_dict.keys())[:3]
                    )
                    
                    return model_dict
                else:
                    _LOGGER.warning(
                        "Failed to fetch /manage page: HTTP %s", response.status
                    )
                    return None
        except Exception as err:
            _LOGGER.warning("Error parsing model details from HTML: %s", err)
            return None

    async def async_shutdown(self) -> None:
        """Close the session."""
        if self.session:
            await self.session.close()
