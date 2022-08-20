# hass-devcontainer

Devcontainer for the development of Lovelace cards and custom components for Home Assistant.

Features:
1. HA Components
    - automatic download of third-party Lovelace cards from Github
    - automatic generation of Lovelace resources list
    - HACS is preinstalled
2. Running HA
    - instantaneous startup because dependencies are already installed
    - colored logs
    - restart HA with a simple key press
3. Development tools
    - preinstalled Playwright dependencies & browsers


## Example usage

.devcontainer/devcontainer.json
```json
{
    "image": "gwisp2/hass-devcontainer:latest",
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

## HA credentials
dev:dev

## Paths
| Path             |  Purpose      |
|-----------------:|:--------------|
| /hdata   | HA data (aka config) directory |
| /henv   | venv where HA is installed |
| /hactl/.venv | venv where hactl is installed, hactl is an utility that controls HA   |
| /usr/bin/hactl   | hactl symlink, links to hactl executable inside venv |

Probably you want to mount `configuration.yaml` or `ui-lovelace.yaml` inside `/hdata`.

## Debugging
hactl always starts debugpy that your connect to from VS Code.

**NB: Enable 'Debug: Show Sub Sessions In Tool Bar' in VS Code settings, [VS Code is buggy without that flag](https://github.com/microsoft/vscode-python/issues/19720)**.


.vscode/launch.json
```
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: attach",
            "type": "python",
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 5678
            },
            "justMyCode": false
        }
    ]
}
```