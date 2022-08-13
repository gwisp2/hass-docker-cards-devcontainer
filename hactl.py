#!/usr/bin/env python3

import itertools
from selectors import EVENT_READ, DefaultSelector
from asyncio.subprocess import DEVNULL, PIPE, STDOUT
import contextlib
from genericpath import exists
from io import BytesIO
import json
import os
from signal import SIGINT
import fcntl
import subprocess
import shlex
import sys
import requests
from pathlib import Path
from typing import Dict, List, Literal, Optional
from rich.console import Console
from rich.live import Live
from rich.status import Status
from rich.console import Group
from rich.padding import Padding
from rich.markup import escape
from select import select
import tempfile
import zipfile

HASS_VENV_DIR = Path("/home/vscode/hass-venv")
HASS_CONFIG_ROOT = Path("/home/vscode/config")
WORKSPACE_DIRECTORY = HASS_CONFIG_ROOT.joinpath('www/workspace')
DOT_STORAGE_DIRECTORY = HASS_CONFIG_ROOT.joinpath('.storage')
LOVELACE_PLUGINS = ["thomasloven/lovelace-card-mod",
                    "thomasloven/lovelace-auto-entities", "custom-cards/button-card"]

plugin_files = []


class TaskException(Exception):
    pass


class TaskLogger:
    """A helper class for writing logs for tasks."""

    Status = Literal["running", "failed", "cancelled", "changed", "no changes"]

    def __init__(self, console: Console, name: str) -> None:
        self._console = console
        self._name: str = name
        self._output: Group = Group()
        self._status: "TaskLogger.Status" = "running"
        self._update_output_header()

    def log(self, renderable):
        self._output.renderables.append(
            Padding(renderable, pad=(0, 0, 0, 3), style="grey50"))

    def mark_no_changes(self):
        self._update_status("no changes")

    @contextlib.contextmanager
    def use(self):
        """
            Starts logging for the task.
            Task logs will be displayed on console under the task header.

            Usage:

                task = Task(console, name)
                with task.use():
                    task.log("Hello")
                    task.log("World")
        """
        with Live(self._output, console=self._console) as live:
            try:
                yield
                if self._status != 'no changes':
                    self._update_status("changed")
            except KeyboardInterrupt:
                self._update_status("cancelled")
                raise
            except:
                self._update_status("failed")
                raise
            finally:
                live.refresh()

    def _update_status(self, new_status: "TaskLogger.Status"):
        self._status = new_status
        self._update_output_header()

    def _update_output_header(self):
        # Compute new header
        if self._status == "running":
            new_header = Status(f" {self._name}", spinner='line')
        elif self._status == "changed":
            new_header = f":white_check_mark: {self._name} \[[green]changed[/]]"
        elif self._status == "no changes":
            new_header = f":sparkles: {self._name} \[[yellow]no changes[/]]"
        elif self._status == "failed" or self._status == "cancelled":
            new_header = f":X: {self._name} \[[red]{self._status}[/]]"

        # Set new header
        if len(self._output.renderables) == 0:
            self._output.renderables.append(new_header)
        else:
            self._output.renderables[0] = new_header


class HaCtl:
    console: Console
    current_task_logger: Optional[TaskLogger]
    plugins_js_files: List[Path]

    def __init__(self) -> None:
        self.console = Console(highlight=False)
        self.current_task_logger = None
        self.plugins_js_files = []

    def install_hass(self, version: str):
        with self.task(f"Installing HASS {escape(version)}"):
            venv_bin_dir = HASS_VENV_DIR.joinpath('bin')
            venv_pip = str(venv_bin_dir.joinpath('pip'))

            if not HASS_VENV_DIR.exists() or len(os.listdir(HASS_VENV_DIR)) == 0:
                self.log(
                    f"Creating virtualenv at {escape(str(HASS_VENV_DIR))}")
                self.run_command(["python", "-m", "venv", str(HASS_VENV_DIR)])

            had_changes = False
            need_install_hass = True
            pip_installed_packages = json.loads(self.run_command(
                [venv_pip, "list", "--format", "json", "--disable-pip-version-check"]).stdout)
            home_assistant_version = next(
                (p["version"] for p in pip_installed_packages if p["name"] == "homeassistant"), None)
            if home_assistant_version is not None:
                if home_assistant_version == version:
                    need_install_hass = False
                else:
                    self.log(
                        f"Home Assistant {escape(home_assistant_version)} is installed, installing {escape(version)} instead")

            if need_install_hass:
                had_changes = True
                self.log(f"Installing to {escape(str(HASS_VENV_DIR))}")
                self.run_command(
                    [venv_pip, "install", f"homeassistant=={version}"])

            additional_packages_to_install = ["sqlalchemy", "fnvhash"]
            pip_installed_packages = json.loads(self.run_command(
                [venv_pip, "list", "--format", "json", "--disable-pip-version-check"]).stdout)
            pip_installed_additional_packages = [
                p["name"] for p in pip_installed_packages if p["name"] in additional_packages_to_install]
            if set(pip_installed_additional_packages).issuperset(set(additional_packages_to_install)):
                had_changes = True
                self.log("Installing additional packages")
                self.run_command(
                    [venv_pip, "install", *additional_packages_to_install])

            if not had_changes:
                self.mark_no_changes()

    def dry_run_and_install_missing_packages(self):
        """
            HA downloads and installs additional python packages during startup.
            Start HA for some time so that all packages are added into docker image.
        """
        with self.task("Dry run HA to install missing packages"):
            venv_bin_dir = HASS_VENV_DIR.joinpath('bin')
            venv_pip = str(venv_bin_dir.joinpath('pip'))

            pip_installed_packages = json.loads(self.run_command(
                [venv_pip, "list", "--format", "json", "--disable-pip-version-check"]).stdout)
            installed_package_names = [p["name"]
                                       for p in pip_installed_packages]
            if "home-assistant-frontend" in installed_package_names:
                # Consider that everything is already installed
                self.mark_no_changes()
                return

            # Forbid using non-virtualenv packages
            subprocess_env = dict(os.environ)
            subprocess_env.pop('PYTHONPATH', None)

            # Run HA in a temporary directory
            with tempfile.TemporaryDirectory() as tmp_dir:
                # Start HA
                hass_command = self.build_hass_command(
                    ["-v"], config_dir=tmp_dir)

                try:
                    proc = subprocess.Popen(
                        hass_command, env=subprocess_env, stdin=DEVNULL, stdout=PIPE, stderr=STDOUT)

                    StartupResult = Literal["timeout", "crash", "ok"]
                    hass_startup_result: Optional[StartupResult] = None
                    unprocessed_bytes = b""

                    # Consider HA hung if it doesn't print logs for that amounts of seconds
                    read_timeout = 60

                    # Make pipe non-blocking
                    pipe_fd = proc.stdout.fileno()
                    pipe_fl = fcntl.fcntl(pipe_fd, fcntl.F_GETFL)
                    fcntl.fcntl(pipe_fd, fcntl.F_SETFL,
                                pipe_fl | os.O_NONBLOCK)

                    # Scan logs
                    log = BytesIO()
                    selector = DefaultSelector()
                    selector.register(proc.stdout, EVENT_READ)
                    try:
                        while hass_startup_result is None:
                            events_list = selector.select(read_timeout)
                            if len(events_list) == 0:
                                # Timeout
                                hass_startup_result = "timeout"
                            else:
                                bytes_read = proc.stdout.read()
                                # Remember everything read so that we can print logs if HA crashes
                                log.write(bytes_read)

                                if len(bytes_read) == 0:
                                    # EOF
                                    hass_startup_result = "crash"
                                else:
                                    # Process bytes
                                    last_bytes = unprocessed_bytes + bytes_read
                                    lines = last_bytes.split(b'\n')
                                    startup_completion_marker_found = next(
                                        (line for line in lines if b'Starting Home Assistant' in line), None) is not None
                                    if startup_completion_marker_found:
                                        # Startup completed
                                        hass_startup_result = "ok"
                                    # Remember uncompleted line
                                    unprocessed_bytes = lines[-1]
                    finally:
                        selector.close()

                    result_descriptions: Dict[StartupResult, str] = {
                        "timeout": f"Timeout. Didn't receive any logs for {read_timeout}s",
                        "crash": f"HA process exited unexpectedly",
                        "ok": f"HA successfully started up"
                    }
                    self.log(result_descriptions[hass_startup_result])
                    if hass_startup_result == "crash":
                        self.log(Padding(log.getvalue().decode(
                            'utf-8', 'ignore'), pad=(0, 0, 0, 3)))
                finally:
                    # Ask HA to terminate if it is still running
                    if proc.poll() is None:
                        self.log("Asking HA to stop")
                        proc.send_signal(SIGINT)
                        try:
                            proc.wait(15)
                        except TimeoutError:
                            self.log("HA didn't react to SIGINT, killing")
                            proc.kill()

                if hass_startup_result != "ok":
                    raise TaskException()

    @contextlib.contextmanager
    def task(self, name: str):
        if self.current_task_logger is not None:
            raise ValueError("Task is already set")

        try:
            self.current_task_logger = TaskLogger(self.console, name)
            with self.current_task_logger.use():
                yield
        finally:
            self.current_task_logger = None

    def log(self, renderable):
        assert(self.current_task_logger is not None)
        self.current_task_logger.log(renderable)

    def mark_no_changes(self):
        assert(self.current_task_logger is not None)
        self.current_task_logger.mark_no_changes()

    def run_command(self, command: List[str], reset_pythonpath=True, catch_output=True, raise_on_error=True) -> subprocess.CompletedProcess[bytes]:
        if reset_pythonpath:
            # Forbid using non-virtualenv packages
            subprocess_env = {k: v for k,
                              v in os.environ.items() if k != 'PYTHONPATH'}
        else:
            subprocess_env = None

        if catch_output:
            result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, check=False, env=subprocess_env)
        else:
            result = subprocess.run(
                command, stdin=subprocess.DEVNULL, check=False, env=subprocess_env)

        if result.returncode == 0 or not raise_on_error:
            return result

        self.log(
            f"Command [red]{escape(shlex.join(command))}[/] exited with exit code [red]{result.returncode}[/]")
        if result.stdout is not None:
            self.log(Padding(escape(result.stdout.decode(
                'utf-8', errors='ignore')), pad=(0, 0, 0, 2)))
        raise TaskException()

    def build_hass_command(self, args: List[str], config_dir=None):
        return [str(HASS_VENV_DIR.joinpath("bin", "hass")), "-c", str(HASS_CONFIG_ROOT) if config_dir is None else config_dir, *args]

    def ensure_hass_config(self):
        with self.task("Ensuring Home Assistant configuration exists"):
            configuration_dir_exists = HASS_CONFIG_ROOT.exists()
            configuration_files_are_present = self.run_command(self.build_hass_command(
                ["--script", "ensure_config"]), raise_on_error=False).returncode == 0

            if not configuration_dir_exists or not configuration_files_are_present:
                self.run_command(self.build_hass_command(
                    ["--script", "ensure_config"]))
            else:
                self.mark_no_changes()

    def create_hass_user(self):
        username = "dev"
        password = "dev"
        with self.task(f"Creating user [blue]{escape(username)}[/]"):
            user_already_added = self.run_command(self.build_hass_command(
                ["--script", "auth", "validate", username, password]), raise_on_error=False).returncode == 0
            if user_already_added:
                self.mark_no_changes()
                return

            self.run_command(self.build_hass_command(
                ["--script", "auth", "add", username, password]))

    def bypass_onboarding(self):
        with self.task(f"Bypassing onboarding"):
            DOT_STORAGE_DIRECTORY.mkdir(exist_ok=True)
            onboarding_data_file = HASS_CONFIG_ROOT.joinpath(
                '.storage/onboarding')

            if onboarding_data_file.exists():
                self.mark_no_changes()
                return

            onboarding_data_file.write_text("""
            {
                "data": {
                    "done": [
                        "user",
                        "core_config",
                        "integration"
                    ]
                },
                "key": "onboarding",
                "version": 3
            }
            """, encoding='utf-8')

    def download_lovelace_plugins(self):
        with self.task(f"Downloading lovelace plugins"):
            WORKSPACE_DIRECTORY.mkdir(exist_ok=True, parents=True)

            if len(LOVELACE_PLUGINS) == 0:
                self.log("No plugins to download")
                return

            n_downloads = 0
            n_failures = 0
            for plugin in LOVELACE_PLUGINS:
                author, repo = plugin.split('/')
                file = repo.removeprefix("lovelace-")
                file_path = WORKSPACE_DIRECTORY.joinpath(file + ".js")
                self.plugins_js_files.append(file_path)

                if file_path.exists():
                    continue

                # Determine where to search for .js files
                # HEAD means the default branch
                possible_download_urls = [
                    f"https://raw.githubusercontent.com/{author}/{repo}/HEAD/{file}.js",
                    f"https://raw.githubusercontent.com/{author}/{repo}/HEAD/dist/{file}.js",
                    f"https://github.com/{author}/{repo}/releases/latest/download/{file}.js",
                    f"https://github.com/{author}/{repo}/releases/latest/download/{file}-bundle.js"
                ]

                # Find file by examining every url
                content = None
                response_status_codes = []
                for possible_url in possible_download_urls:
                    response = requests.get(possible_url)

                    if 200 <= response.status_code <= 299:
                        content = response.content
                        break

                    response_status_codes.append(response.status_code)

                # All urls failed
                if content is None:
                    self.log(
                        f"[red]Failed to download [blue]{escape(plugin)}[/][/]")
                    for download_url, code in zip(possible_download_urls, response_status_codes):
                        self.log(
                            f"[red]HTTP {code} - [blue]{download_url}[/blue]")
                    n_failures += 1
                    continue

                # Save downloaded file
                self.log(f"Saving [blue]{escape(str(file_path))}[/]")
                file_path.write_bytes(content)

            if n_failures != 0:
                raise TaskException()
            if n_downloads == 0:
                self.mark_no_changes()

    def generate_lovelace_resources(self):
        with self.task("Generating Lovelace resources list"):
            paths = [str(file.relative_to(WORKSPACE_DIRECTORY))
                     for file in self.plugins_js_files]
            config = {
                "data": {
                    "items": [{
                        "id": f"{i}",
                        "type": "module",
                        "url": f"{p}"
                    } for i, p in enumerate(paths)]
                },
                "key": "lovelace_resources",
                "version": 1
            }

            lovelace_config_file = DOT_STORAGE_DIRECTORY.joinpath(
                "lovelace_resources")
            lovelace_config_file_content = lovelace_config_file.read_text(
                'utf-8') if lovelace_config_file.exists() else None
            new_config_as_text = json.dumps(config)

            if new_config_as_text == lovelace_config_file_content:
                self.mark_no_changes()
                return

            self.log(f"{len(self.plugins_js_files)} plugin(s) found")
            lovelace_config_file.write_text(json.dumps(config), 'utf-8')

    def download_hacs(self):
        with self.task("Downloading HACS"):
            hacs_dest_dir = HASS_CONFIG_ROOT.joinpath('custom_components/hacs')
            if hacs_dest_dir.exists():
                self.mark_no_changes()
                return

            hacs_fetch_url = 'https://github.com/hacs/integration/releases/latest/download/hacs.zip'
            response = requests.get(hacs_fetch_url)
            if 200 <= response.status_code < 299:
                hacs_dest_dir.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(BytesIO(response.content)) as zip:
                    zip.extractall(hacs_dest_dir)
            else:
                self.log(
                    f"HTTP {response.status_code} - {escape(hacs_fetch_url)}")
                raise TaskException()

    def run_hass(self):
        with self.task("Running Home Assistant"):
            pass


def main():
    try:
        ctl = HaCtl()
        ctl.install_hass("2022.8.3")
        ctl.ensure_hass_config()
        ctl.create_hass_user()
        ctl.bypass_onboarding()
        ctl.download_lovelace_plugins()
        ctl.generate_lovelace_resources()
        ctl.download_hacs()
        ctl.dry_run_and_install_missing_packages()
        # ctl.run_hass()
    except KeyboardInterrupt:
        # Exit silently
        pass
    except TaskException:
        sys.exit(1)


if __name__ == '__main__':
    main()
