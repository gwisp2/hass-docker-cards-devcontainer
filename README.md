# hass-devcontainer

Devcontainer for the development of Lovelace cards and custom components for Home Assistant.

Features:
1. HA Components
    - automatic download of third-party Lovelace cards from Github
    - automatic generation of Lovelace resources list (with your cards included)
    - HACS is preinstalled
    - automatic download of custom components from git
    - automatic creation of symlinks from custom_components to your code
2. Running HA
    - instantaneous startup because dependencies are already installed
    - colored logs
    - restart HA with a simple key press
    - ready-for-attach debug adapter is listening on port 5678
3. Development tools
    - Playwright dependencies & browsers
    - poetry and poethepoet
    - node.js 16 (with nvm)
    - sqlite3 cli

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
        "source=${localWorkspaceFolder}/.devcontainer/02-custom.yaml,target=/etc/hactl/02-custom.yaml,type=bind"
    ]
}
```

.devcontainer/02-custom.yaml
```yaml
lovelace:
    plugins: ["piitaya/lovelace-mushroom"]
    extra_files: ["dist/my-super-card.js"]

# hactl will recursively search for manifest.json and the symlink to parent of manifest.json will be added to custom_components
customComponents:
    - path: /path/my/super_component
    - git: gwisp2/hass-time-machine#main
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
hactl always starts debugpy that can be attached from VS Code.
Use `--wait-for-debugger` if you need to attach debugger before startup.

**Warning: enable 'Debug: Show Sub Sessions In Tool Bar' in VS Code settings, [VS Code is buggy without that flag](https://github.com/microsoft/vscode-python/issues/19720)**.

**Warning: your component code is accessed through a symlink, configure [path mappings](https://code.visualstudio.com/docs/python/debugging) or your breakpoints won't work.**


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