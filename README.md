# LocalAI Monitor - Home Assistant Integration

A Home Assistant custom integration for monitoring LocalAI instances. Track installed models, backends, system resources, and manage running models directly from Home Assistant.

## Features

- **Model Monitoring**: Track all installed models with detailed information including:
  - Backend type (llama-cpp, whisper, stablediffusion, etc.)
  - Runtime status (Running, Idle)
  - Use cases (Chat, TTS, Image, Audio)
  - MCP (Model Context Protocol) status
  
- **Backend Tracking**: Monitor installed backends and their metadata

- **System Monitoring**: Track system information and resource usage

- **Model Management**: Shutdown running models to free up resources via Home Assistant services

- **Jobs Monitoring**: Track model loading and processing jobs

## Installation

### HACS (Recommended)

1. Add this repository as a custom repository in HACS:
   - Go to HACS → Integrations → ⋮ (menu) → Custom repositories
   - Add: `https://github.com/loryanstrant/HA-LocalAI-Monitor`
   - Category: Integration

2. Click "Download" on the LocalAI Monitor integration
3. Restart Home Assistant
4. Go to Settings → Devices & Services → Add Integration
5. Search for "LocalAI Monitor"

### Manual Installation

1. Copy the `custom_components/localai_monitor` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Go to Settings → Devices & Services → Add Integration
4. Search for "LocalAI Monitor"

## Configuration

Configure the integration through the UI:

- **URL**: Your LocalAI instance URL (e.g., `http://localhost:8080`)
- **API Key**: (Optional) Your LocalAI API key if authentication is enabled
- **Verify SSL**: Whether to verify SSL certificates
- **Scan Interval**: How often to poll LocalAI for updates (default: 60 seconds)

## Sensors

The integration provides the following sensors:

### Installed Models
- **State**: Number of installed models
- **Attributes**: Detailed list of models with backend, status, use cases, and MCP status

### Installed Backends
- **State**: Number of installed backends
- **Attributes**: List of backends with installation metadata

### System
- **State**: System status
- **Attributes**: System information from LocalAI

### Resources
- **State**: Resource status
- **Attributes**: Resource usage information

### Model Jobs
- **State**: Number of active jobs
- **Attributes**: List of running model jobs

## Services

### `localai_monitor.shutdown_model`

Shut down a specific model to free up resources.

**Parameters:**
- `model_name` (required): The name of the model to shut down (e.g., "gpt-4", "llama3-instruct")

**Example:**
```yaml
service: localai_monitor.shutdown_model
data:
  model_name: "gpt-4"
```

## Use Cases

### Automation Example: Shutdown Idle Models

```yaml
automation:
  - alias: "Shutdown idle LocalAI models at night"
    trigger:
      - platform: time
        at: "23:00:00"
    action:
      - service: localai_monitor.shutdown_model
        data:
          model_name: "gpt-4"
```

### Dashboard Example

Display model information in your dashboard:

```yaml
type: entities
entities:
  - entity: sensor.localai_monitor_installed_models
    name: Models
  - entity: sensor.localai_monitor_installed_backends
    name: Backends
  - entity: sensor.localai_monitor_system
    name: System Status
```

## Technical Details

- **Model Information Source**: The integration parses LocalAI's `/manage` page HTML to extract detailed model information (backend, status, use cases) since this data isn't available via the API
- **API Endpoints Used**:
  - `/v1/models` - Model list
  - `/backends` - Backend information
  - `/models/jobs` - Job status
  - `/system` - System information
  - `/api/resources` - Resource usage
  - `/manage` - HTML parsing for detailed model data
  - `/backend/shutdown` - Model shutdown endpoint

## Requirements

- Home Assistant 2025.10.0 or newer
- A running LocalAI instance

## Support

For issues, feature requests, or contributions, please visit the [GitHub repository](https://github.com/loryanstrant/HA-LocalAI-Monitor).

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Credits

Developed by [@loryanstrant](https://github.com/loryanstrant)
