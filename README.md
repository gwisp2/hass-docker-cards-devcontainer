# hass-docker-cards-devcontainer
A docker container for developing and testing custom Lovelace cards.
This repository is forked from [thomasloven/hass-custom-devcontainer](https://github.com/thomasloven/hass-custom-devcontainer) to solve issue when postCreateCommand is running infinitely therefore some VS Code actions like copying .gitconfig are not performed.

## Usage with docker
```
docker run --rm -it \
    -p 8123:8123 \
    -v $(pwd):/workspaces/test \
    -v $(pwd):/config/www/workspace \
    -e LOVELACE_LOCAL_FILES="mycard.js"
    -e LOVELACE_PLUGINS="thomasloven/lovelace-card-mod thomasloven/lovelace-auto-entities custom-cards/button-card" \
    gwisp2/hass-docker-cards-devcontainer
```

Image has the following components preinstalled:
- Home Assistant
- [TheToken custom component](https://github.com/gwisp2/hass-the-token). You can use the autogenerated access token to use scripts that utilize HA REST or WS API. TheToken will not be started without an entry in the `configuration.yaml`.

The default action of the image is to run `sudo -E hactl setup-run`, which will
- Make sure there's a basic Home Assistant configuration in `/config`
- Add a default admin user to Home Assistant (named `dev` with password `dev`)
- Skip the onboarding procedure
- Download and install [HACS](https://hacs.xyz)
- Download Lovelace plugins from Github
- Add plugins to lovelace configuration from local files
- Start Home Assistant with `-v`

### Environment Variables

| Name | Description | Default |
|---|---|---|
| `HASS_USERNAME` | The username of the default user | `dev` |
| `HASS_PASSWORD` | The password of the default user | `dev` |
| `LOVELACE_PLUGINS` | List of Lovelace plugins to download from github | Empty |
| `LOVELACE_LOCAL_FILES` | List of filenames relative to `/config/www/workspace` that should be added as lovelace resources | Empty |

### About Lovelace Plugins
The download and installation of plugins are _very_ basic. This is not HACS.

`LOVELACE_PLUGINS` should be a space-separated list of author/repo pairs, e.g. `"thomasloven/lovelace-card-mod  kalkih/mini-media-player"`

`LOVELACE_LOCAL_FILES` is for the currently worked on plugins and should be a list of file names that are mounted in `/config/www/workspace`.

### hactl script

```bash
# Creates the default user, downloads HACS and installs Lovelace plugins. root is mandatory to write to `/config`.
hactl setup
```

```bash
# Runs HomeAssistant in foreground. Intended to be used when running docker directly.
# Launches hass -c /config -v
# Also this command is used by supervisord to run Home Assistant.
hactl run
```

```bash
# Starts Home Assistant in background with supervisord and outputs logs until Home Assistant startup completes. root is not required.
hactl start
```

```bash
# Combinations of commands above
hactl setup-run
hactl setup-start
```

### hassfest
`hassfest` script remained from the original repository. I don't know what it does but I guess it is useful.

## devcontainer.json example

Note that the default image command is not run when used as a devcontainer.

```json
{
    "image": "gwisp2/hass-docker-cards-devcontainer:latest",
    "postCreateCommand": "sudo /usr/bin/supervisord && sudo -E hactl setup-start",
    "forwardPorts": [8123],
    "mounts": [
        "source=${localWorkspaceFolder},target=/config/www/workspace,type=bind",
        "source=${localWorkspaceFolder}/configuration.yaml,target=/config/configuration.yaml,type=bind"
    ]
}
```
