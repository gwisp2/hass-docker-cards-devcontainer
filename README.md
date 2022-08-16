# hass-docker-cards-dev

Devcontainer for development of Lovelace cards for Home Assistant.

Features:
1. Automatic download of Lovelace cards from GitHub
2. Automatic generation of lovelace resources list
3. Easy to restart HA, just stop HA with `Ctrl+C` and select 'start HA', that feature can be useful when using custom components.
4. Preinstalled HACS
5. Can be used offline. HA downloads extra packages on the first run, and the first run is made done building this image.

## Example usage

.devcontainer/devcontainer.json
```json
{
    "image": "gwisp2/hass-docker-cards-devcontainer:latest",
    "postStartCommand": "sudo hactl run",
    "forwardPorts": [
        8123
    ],
    "mounts": [
        // Mount your workspace directory
        "source=${localWorkspaceFolder},target=/opt/hass/data/www/workspace,type=bind",

        // Mount file with additional configuration
        "source=${localWorkspaceFolder}/.devcontainer/02-custom.yaml,target=/etc/hactl/02-lovelace.yaml,type=bind"
    ]
}
```

.devcontainer/02-custom.yaml
```yaml
lovelace:
    plugins: ["piitaya/lovelace-mushroom"]
    extra_files: ["dist/my-super-card.js"]
```

## Paths
| Path             |  Purpose      |
|-----------------:|:--------------|
| /opt/hass/data   | HA data (aka config) directory |
| /opt/hass/venv   | venv where HA is installed |
| /opt/hactl/.venv | venv where hactl is installed, hactl is an utility that controls HA   |
| /usr/bin/hactl   | hactl symlink, links to hactl executable inside venv |

Probably you want to mount `configuration.yaml` or `ui-lovelace.yaml` inside `/opt/hass/data/`.