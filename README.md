# hass-docker-cards-dev

Devcontainer for development of Lovelace cards for Home Assistant.

Features:
1. Components
    - automatic download of third-party Lovelace cards from Github
    - automatic generation of Lovelace resources list
    - HACS is preinstalled
3. Instantaneous startup: usually HA downloads different stuff on the first run, and in this image, everything is already downloaded for you.
4. Preinstalled Playwright dependencies & browsers. Useful if you want to make screenshots of your custom cards.

## Example usage

.devcontainer/devcontainer.json
```json
{
    "image": "gwisp2/hass-docker-cards-devcontainer:latest",
    "postStartCommand": "hactl run",
    "forwardPorts": [
        8123
    ],
    "mounts": [
        // Mount your workspace directory
        "source=${localWorkspaceFolder},target=/hdata/www/workspace,type=bind",

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
| /hdata   | HA data (aka config) directory |
| /henv   | venv where HA is installed |
| /hactl/.venv | venv where hactl is installed, hactl is an utility that controls HA   |
| /usr/bin/hactl   | hactl symlink, links to hactl executable inside venv |

Probably you want to mount `configuration.yaml` or `ui-lovelace.yaml` inside `/opt/hass/data/`.