""" Tests for the distribution container """
import json
import os

import pytest
from pytest_container import OciRuntimeBase

from bci_tester.data import DISTRIBUTION_CONTAINER
from bci_tester.runtime_choice import DOCKER_SELECTED

CONTAINER_IMAGES = [DISTRIBUTION_CONTAINER]


def test_registry_service(
    host, auto_container_per_test, tmp_path, container_runtime: OciRuntimeBase
):
    """run registry container with attached volume '/var/lib/docker-registry'"""
    engine = container_runtime.runner_binary
    host_port = auto_container_per_test.forwarded_ports[0].host_port
    content = """FROM alpine:latest
    CMD ["echo", "container from my local registry"]
    """

    out = host.check_output(
        f"curl -sb -H 'Accept: application/json' http://localhost:{host_port}/v2/_catalog"
    )
    assert out == '{"repositories":[]}'

    container_tag = "test_container"
    container_path = f"localhost:{host_port}/{container_tag}"

    host.run(f"{engine} logs {auto_container_per_test.container_id}")
    # build custom image to be pushed into the registry container
    with open(tmp_path / "Containerfile", "w", encoding="utf-8") as cfile:
        cfile.write(content)
    host.run_expect(
        [0],
        f"""
cd {tmp_path} && {' '.join(container_runtime.build_command)} \
    -t {container_path} -f Containerfile .
""",
    )

    force_http_mode = ""
    if container_runtime.runner_binary == "podman":
        force_http_mode = "--tls-verify=false"

    host.run_expect(
        [0],
        f"{engine} push {force_http_mode} {container_path}",
    )
    out = host.check_output(
        f"curl -sb -H 'Accept: application/json' http://localhost:{host_port}/v2/_catalog"
    )
    assert out == '{"repositories":["test_container"]}'

    host.run_expect([0], f"{engine} rmi {container_path}")
    host.run_expect(
        [0],
        f"{engine} pull {container_path}",
    )
    host.run_expect([0], f"{engine} run --rm {container_path}")
