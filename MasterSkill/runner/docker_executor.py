"""Docker executor for skill evaluation."""

import json
import os
import io
import hashlib
import re
import shlex
import shutil
import subprocess
import tarfile
import tempfile
import time
import requests
from types import SimpleNamespace
from datetime import datetime
from pathlib import Path
from typing import Optional
import urllib3

try:
    import docker
except ImportError:
    docker = None

from ..core.paths import resolve_task_dir
from ..core.types import SkillBundle
from .task_router import TaskRouter


class DockerExecutor:
    """Executes skills in Docker containers for evaluation.

    Flow:
    1. Build container from task's Dockerfile
    2. Copy skill to container's skills directory
    3. Run model with skill in container
    4. Capture output and execution log
    5. Return results for Judger evaluation
    """

    def __init__(self, skillsbench_root: str):
        if docker is None:
            raise RuntimeError(
                "The Python 'docker' package is required to run MasterSkill. "
                "Install it before executing benchmark tasks."
            )
        self.skillsbench_root = Path(skillsbench_root)
        self.task_router = TaskRouter(skillsbench_root)
        self.debug = os.environ.get("MASTERSKILL_DEBUG", "").lower() in {"1", "true", "yes"}
        configured_build_network = os.environ.get("MASTERSKILL_DOCKER_BUILD_NETWORK", "host").strip()
        self.build_network_mode = configured_build_network or None
        last_exc = None
        for attempt in range(1, 5):
            try:
                self.client = docker.from_env()
                break
            except Exception as exc:
                last_exc = exc
                if attempt >= 4:
                    raise RuntimeError(
                        "Docker is not available from this environment. "
                        "Install the Docker SDK and ensure the Docker engine is reachable. "
                        f"Original error: {exc}"
                    ) from exc
                self._log(
                    f"docker client init failed attempt={attempt}/4; retrying. reason={exc}"
                )
                time.sleep(min(3 * attempt, 10))

    def _log(self, message: str) -> None:
        """Emit lightweight debug logs when requested."""
        if self.debug:
            print(f"[DockerExecutor] {message}", flush=True)

    def execute_skill(
        self,
        task_id: str,
        skill: SkillBundle,
        instruction: str,
        output_path: str = "",
        timeout: int = 900,
    ) -> dict:
        """Execute a skill in Docker and return results.

        Returns:
            {
                "success": bool,
                "output_file": str,      # Content of output_path
                "execution_log": str,    # Terminal output
                "error": str,            # Error message if any
                "exit_code": int,
                "model": str,
                "reasoning_effort": str,
                "duration_seconds": float,
                "difficulty": str,
                "routing_reason": str,
                "failure_class": str,
                "input_tokens": int,
                "cached_input_tokens": int,
                "output_tokens": int,
            }
        """
        task_dir = resolve_task_dir(self.skillsbench_root, task_id)
        if not self._task_has_dockerfile(task_dir):
            return {
                "success": False,
                "output_file": "",
                "execution_log": "",
                "error": f"Dockerfile not found: {task_dir / 'environment' / 'Dockerfile'}",
                "exit_code": -1,
            }

        image_name = f"masterskill:{task_id}"
        self._log(f"execute_skill task={task_id} image={image_name}")
        self._build_image(task_dir, image_name)

        container = None
        try:
            container = self._start_container(image_name)
            self._write_instruction(container, instruction)
            task_local_skill_ids = {path.name for path in self._task_local_skill_dirs(task_id)}
            self._copy_task_local_skills(container, task_id)
            if skill.skill_id not in task_local_skill_ids:
                self._copy_skill(container, skill)

            exec_result = self._run_agent(
                task_id=task_id,
                container=container,
                instruction=instruction,
                skill=skill,
                output_path=output_path,
                timeout=timeout,
            )
            execution_log = self._decode_output(exec_result.output)
            artifact_summary = self._build_artifact_report(container, output_path)
            combined_parts: list[str] = []
            if artifact_summary:
                combined_parts.append(f"[Output Artifacts]\n{artifact_summary}")
            if execution_log:
                combined_parts.append(f"[Execution Log]\n{execution_log}")
            combined_log = "\n\n".join(part for part in combined_parts if part)
            failure_class = self._classify_failure(
                output=combined_log,
                exit_code=exec_result.exit_code,
                passed=exec_result.exit_code == 0,
            )
            if getattr(exec_result, "failure_class", ""):
                failure_class = exec_result.failure_class

            return {
                "success": exec_result.exit_code == 0,
                "output_file": self._get_file(container, output_path) if output_path else "",
                "execution_log": combined_log,
                "error": "" if exec_result.exit_code == 0 else "Execution failed",
                "exit_code": exec_result.exit_code,
                "model": exec_result.model,
                "reasoning_effort": exec_result.reasoning_effort,
                "duration_seconds": exec_result.duration_seconds,
                "difficulty": exec_result.difficulty,
                "routing_reason": exec_result.routing_reason,
                "failure_class": failure_class,
                "input_tokens": exec_result.input_tokens,
                "cached_input_tokens": exec_result.cached_input_tokens,
                "output_tokens": exec_result.output_tokens,
            }
        finally:
            if container is not None:
                container.remove(force=True)

    def run_real_test(
        self,
        task_id: str,
        instruction: str,
        skill: Optional[SkillBundle] = None,
        timeout: int = 900,
        include_task_local_skills: bool = True,
    ) -> dict:
        """Run the official SkillsBench test.

        Returns:
            {
                "passed": bool,
                "score": float,        # 0.0 - 1.0
                "details": str,        # Test output
                "exit_code": int,
                "model": str,
                "reasoning_effort": str,
                "execution_duration_seconds": float,
                "test_duration_seconds": float,
                "duration_seconds": float,
                "difficulty": str,
                "routing_reason": str,
                "failure_class": str,
                "input_tokens": int,
                "cached_input_tokens": int,
                "output_tokens": int,
            }
        """
        task_dir = resolve_task_dir(self.skillsbench_root, task_id)
        test_file = task_dir / "tests" / "test_outputs.py"
        test_script = task_dir / "tests" / "test.sh"
        if not test_file.exists() and not test_script.exists():
            return {
                "passed": False,
                "score": 0.0,
                "details": "Test file not found",
                "exit_code": -1,
                "model": "",
                "reasoning_effort": "",
                "execution_duration_seconds": 0.0,
                "test_duration_seconds": 0.0,
                "duration_seconds": 0.0,
                "difficulty": "",
                "routing_reason": "",
                "failure_class": "missing_test_file",
                "input_tokens": 0,
                "cached_input_tokens": 0,
                "output_tokens": 0,
            }

        image_name = f"masterskill:{task_id}"
        self._log(f"run_real_test task={task_id} image={image_name}")
        self._build_image(task_dir, image_name)
        runtime_image_name = self._prepare_test_runtime_image(task_id, task_dir, image_name)
        self._log(f"runtime_image task={task_id} image={runtime_image_name}")

        exec_container = None
        eval_container = None
        try:
            exec_container = self._start_container(runtime_image_name)
            self._write_instruction(exec_container, instruction)
            if include_task_local_skills:
                task_local_skill_ids = {path.name for path in self._task_local_skill_dirs(task_id)}
                self._copy_task_local_skills(exec_container, task_id)
            else:
                task_local_skill_ids = set()
            if skill is not None:
                if skill.skill_id not in task_local_skill_ids:
                    self._copy_skill(exec_container, skill)

            exec_result = self._run_agent(
                task_id=task_id,
                container=exec_container,
                instruction=instruction,
                skill=skill,
                output_path="",
                timeout=timeout,
                include_task_local_skills=include_task_local_skills,
            )
            artifact_report = self._build_artifact_report(exec_container)
            artifact_paths = self._materialize_execution_artifacts(exec_container)
            eval_container = self._start_container(runtime_image_name)
            self._restore_execution_artifacts(eval_container, artifact_paths)
            self._copy_tests(eval_container, task_dir)
            test_started_at = time.monotonic()
            test_result = self._run_tests(eval_container, timeout)
            test_duration = time.monotonic() - test_started_at

            details_parts: list[str] = []
            if artifact_report:
                details_parts.append("[Output Artifacts]\n" + artifact_report)
            execution_log = self._decode_output(exec_result.output)
            if execution_log:
                details_parts.append("[Execution Log]\n" + execution_log)
            details_parts.append(
                "[Evaluation Mode]\n"
                + "Official tests ran in a fresh container restored only with execution artifacts.\n"
            )
            test_output = self._decode_output(test_result.output)
            if test_output:
                details_parts.append("[Test Output]\n" + test_output)
            details = "\n\n".join(part for part in details_parts if part)
            passed = exec_result.exit_code == 0 and test_result.exit_code == 0
            failure_class = self._classify_failure(
                output=details,
                exit_code=test_result.exit_code if exec_result.exit_code == 0 else exec_result.exit_code,
                passed=passed,
            )
            if getattr(exec_result, "failure_class", ""):
                failure_class = exec_result.failure_class
            return {
                "passed": passed,
                "score": 1.0 if passed else 0.0,
                "details": details,
                "exit_code": test_result.exit_code,
                "model": exec_result.model,
                "reasoning_effort": exec_result.reasoning_effort,
                "execution_duration_seconds": exec_result.duration_seconds,
                "test_duration_seconds": test_duration,
                "duration_seconds": exec_result.duration_seconds + test_duration,
                "difficulty": exec_result.difficulty,
                "routing_reason": exec_result.routing_reason,
                "failure_class": failure_class,
                "input_tokens": exec_result.input_tokens,
                "cached_input_tokens": exec_result.cached_input_tokens,
                "output_tokens": exec_result.output_tokens,
            }
        finally:
            if eval_container is not None:
                eval_container.remove(force=True)
            if exec_container is not None:
                exec_container.remove(force=True)

    def run_task(
        self,
        task_id: str,
        instruction: str,
        output_path: str = "",
        skill_path: Optional[str] = None,
        timeout: int = 900,
        include_task_local_skills: bool = True,
    ) -> dict:
        """Run a task in Docker (without skill).

        This is the initial model attempt to see if the task can be solved
        without any external skill.

        Returns:
            {
                "passed": bool,
                "output": str,       # Content of output_path
                "execution_log": str, # Terminal output
                "error": str,
                "exit_code": int,
            }
        """
        test_result = self.run_real_test(
            task_id=task_id,
            instruction=instruction,
            skill=None,
            timeout=timeout,
            include_task_local_skills=include_task_local_skills,
        )
        return {
            "passed": test_result["passed"],
            "output": "",
            "execution_log": test_result["details"],
            "error": "" if test_result["passed"] else "Model could not solve autonomously",
            "exit_code": test_result["exit_code"],
            "model": test_result.get("model", ""),
            "reasoning_effort": test_result.get("reasoning_effort", ""),
            "duration_seconds": test_result.get("duration_seconds", 0.0),
            "difficulty": test_result.get("difficulty", ""),
            "routing_reason": test_result.get("routing_reason", ""),
            "failure_class": test_result.get("failure_class", ""),
            "score": test_result.get("score", 0.0),
            "input_tokens": test_result.get("input_tokens", 0),
            "cached_input_tokens": test_result.get("cached_input_tokens", 0),
            "output_tokens": test_result.get("output_tokens", 0),
        }

    def _task_has_dockerfile(self, task_dir: Path) -> bool:
        return (task_dir / "environment" / "Dockerfile").exists()

    def _get_image_name(self, task_id: str) -> str:
        """Get image name for a task."""
        return f"skillsbench:{task_id}"

    def _build_image(self, task_dir: Path, image_name: str) -> None:
        """Build Docker image from Dockerfile, skipping rebuilds for identical contexts."""
        context_path = task_dir / "environment"
        context_hash = self._hash_tree(context_path)
        existing = self._get_image(image_name)
        if existing:
            existing_hash = existing.labels.get("masterskill.context_hash")
            if existing_hash == context_hash:
                self._log(f"image cache hit image={image_name}")
                return
            if self._can_reuse_existing_image_for_skill_only_changes(existing, context_path):
                self._log(f"image cache hit image={image_name} reason=skill_only_changes")
                return
            if not existing_hash:
                self._log(f"legacy image cache hit image={image_name}")
                return
        with tempfile.TemporaryDirectory(prefix=f"masterskill-build-{task_dir.name}-") as tmpdir:
            workspace = Path(tmpdir) / "context"
            shutil.copytree(context_path, workspace)
            dockerfile = workspace / "Dockerfile"
            dockerfile.write_text(
                self._rewrite_dockerfile_for_resilient_builds(
                    dockerfile.read_text(),
                    build_timeout_seconds=self._task_build_timeout_seconds(task_dir),
                )
            )
            self._docker_build(
                context_path=workspace,
                dockerfile="Dockerfile",
                tag=image_name,
                labels={
                    "masterskill.context_hash": context_hash,
                    "masterskill.task_id": task_dir.name,
                },
            )

    def _start_container(self, image_name: str):
        """Start a task container and keep it running for host-side Codex control."""
        return self.client.containers.run(
            image_name,
            detach=True,
            command=["bash", "-lc", "while true; do sleep 3600; done"],
            mem_limit="4g",
            cpu_period=100000,
            cpu_quota=200000,
        )

    def _prepare_test_runtime_image(self, task_id: str, task_dir: Path, base_image_name: str) -> str:
        """Build a task-scoped runtime image with common verifier dependencies prewarmed."""
        test_script = task_dir / "tests" / "test.sh"
        if not test_script.exists():
            return base_image_name

        bootstrap = self._extract_test_bootstrap_commands(
            test_script.read_text(),
            build_timeout_seconds=self._task_build_timeout_seconds(task_dir),
        )
        if not bootstrap:
            self._log(f"no verifier bootstrap needed task={task_id}")
            return base_image_name

        base_image = self._get_image(base_image_name)
        if base_image is None:
            return base_image_name

        setup_hash = hashlib.sha256(
            ("\n".join(bootstrap) + "\n" + base_image.id).encode("utf-8")
        ).hexdigest()
        prepared_image_name = f"masterskill:{task_id}-test-runtime"
        existing = self._get_image(prepared_image_name)
        if existing and existing.labels.get("masterskill.test_setup_hash") == setup_hash:
            self._log(f"test runtime cache hit image={prepared_image_name}")
            return prepared_image_name

        with tempfile.TemporaryDirectory(prefix=f"masterskill-test-image-{task_id}-") as tmpdir:
            workspace = Path(tmpdir)
            dockerfile = workspace / "Dockerfile"
            dockerfile.write_text(
                f"FROM {base_image_name}\n"
                "SHELL [\"/bin/bash\", \"-lc\"]\n"
                + self._pip_env_block()
                + "".join(f"RUN {command}\n" for command in bootstrap)
            )
            try:
                self._docker_build(
                    context_path=workspace,
                    dockerfile="Dockerfile",
                    tag=prepared_image_name,
                    labels={
                        "masterskill.test_setup_hash": setup_hash,
                        "masterskill.base_image_id": base_image.id,
                        "masterskill.task_id": task_id,
                    },
                )
                return prepared_image_name
            except docker.errors.BuildError as exc:
                self._log(
                    f"test runtime prewarm failed task={task_id}; falling back to base image. "
                    f"reason={self._truncate_build_error(exc)}"
                )
                return base_image_name
        return base_image_name

    def _extract_test_bootstrap_commands(
        self,
        script_text: str,
        build_timeout_seconds: Optional[int] = None,
    ) -> list[str]:
        """Extract common verifier bootstrap steps that are safe to prewarm."""
        commands: list[str] = []
        apt_packages: list[str] = []
        pip_packages: list[str] = []
        uvx_with_packages: list[str] = []
        build_timeout = build_timeout_seconds or self._apt_build_timeout_seconds()

        for line in self._iter_shell_commands(script_text):
            if not line or line.startswith("#"):
                continue
            apt_match = re.match(r"apt-get install -y (.+)", line)
            if apt_match:
                apt_packages.extend(pkg for pkg in apt_match.group(1).split() if pkg)
                continue
            pip_match = re.match(r"pip3 install(?: --break-system-packages)? (.+)", line)
            if pip_match:
                tail = pip_match.group(1)
                if "&&" not in tail and "||" not in tail:
                    pip_packages.extend(pkg for pkg in tail.split() if pkg)
                continue
            uvx_with_packages.extend(self._extract_uvx_with_packages(line))

        if apt_packages:
            unique_packages = " ".join(dict.fromkeys(apt_packages))
            commands.append(
                f"{self._apt_update_command(build_timeout)} && "
                f"{self._apt_install_command(unique_packages, build_timeout)}"
            )

        if "uvx" in script_text:
            install_uv_bsp = self._pip_install_command("pip3", "uv", break_system_packages=True)
            install_uv_plain = self._pip_install_command("pip3", "uv")
            commands.append(
                "if ! command -v uvx >/dev/null 2>&1; then "
                "if command -v pip3 >/dev/null 2>&1; then "
                f"{install_uv_bsp} || {install_uv_plain}; "
                "fi; "
                "fi"
            )

        if uvx_with_packages:
            uvx_args = " ".join(f"--with {shlex.quote(pkg)}" for pkg in dict.fromkeys(uvx_with_packages))
            commands.append(
                "if command -v uv >/dev/null 2>&1; then "
                f"uv tool run {uvx_args} pytest --version >/dev/null 2>&1 || true; "
                "fi"
            )

        if pip_packages:
            unique_packages = " ".join(dict.fromkeys(pip_packages))
            install_deps_bsp = self._pip_install_command(
                "pip3", unique_packages, break_system_packages=True
            )
            install_deps_plain = self._pip_install_command("pip3", unique_packages)
            commands.append(
                f"if command -v pip3 >/dev/null 2>&1; then "
                f"{install_deps_bsp} || {install_deps_plain}; "
                "fi"
            )

        return commands

    def _iter_shell_commands(self, script_text: str) -> list[str]:
        """Collapse line-continuation shell commands into single logical lines."""
        commands: list[str] = []
        current = ""
        for raw_line in script_text.splitlines():
            stripped = raw_line.strip()
            if not stripped:
                if current:
                    commands.append(current.strip())
                    current = ""
                continue
            if stripped.startswith("#") and not current:
                commands.append(stripped)
                continue
            if stripped.endswith("\\"):
                current += stripped[:-1].strip() + " "
                continue
            current += stripped
            commands.append(current.strip())
            current = ""
        if current:
            commands.append(current.strip())
        return commands

    def _extract_uvx_with_packages(self, line: str) -> list[str]:
        """Extract packages from `uvx --with ...` commands."""
        if "uvx" not in line or "--with" not in line:
            return []
        try:
            tokens = shlex.split(line)
        except ValueError:
            return []

        packages: list[str] = []
        for index, token in enumerate(tokens):
            if token == "--with" and index + 1 < len(tokens):
                packages.append(tokens[index + 1])
        return packages

    def _docker_build(
        self,
        context_path: Path,
        dockerfile: str,
        tag: str,
        labels: dict[str, str],
    ) -> None:
        """Build a Docker image with lightweight retries for transient network failures."""
        max_attempts = 3
        last_exc = None
        use_build_network = True
        for attempt in range(1, max_attempts + 1):
            try:
                build_kwargs = {
                    "path": str(context_path),
                    "dockerfile": dockerfile,
                    "tag": tag,
                    "rm": True,
                    "labels": labels,
                    "use_config_proxy": True,
                }
                if use_build_network and self.build_network_mode:
                    build_kwargs["network_mode"] = self.build_network_mode
                network_label = build_kwargs.get("network_mode", "default")
                self._log(
                    f"building image={tag} attempt={attempt}/{max_attempts} "
                    f"network={network_label}"
                )
                self.client.images.build(
                    **build_kwargs,
                )
                return
            except docker.errors.APIError as exc:
                if use_build_network and self._should_retry_without_build_network(exc):
                    self._log(
                        f"build network={self.build_network_mode} unsupported for image={tag}; "
                        "retrying with default build networking"
                    )
                    use_build_network = False
                    continue
                raise
            except docker.errors.BuildError as exc:
                last_exc = exc
                message = self._build_error_text(exc)
                retryable = self._is_retryable_build_error(message)
                self._log(
                    f"build failed image={tag} attempt={attempt}/{max_attempts} "
                    f"retryable={retryable}"
                )
                if attempt >= max_attempts or not retryable:
                    raise
                time.sleep(min(10 * attempt, 30))
            except (
                urllib3.exceptions.ProtocolError,
                requests.exceptions.ConnectionError,
                BrokenPipeError,
                ConnectionError,
            ) as exc:
                last_exc = exc
                message = self._build_error_text(exc)
                retryable = self._is_retryable_build_error(message)
                self._log(
                    f"build transport failed image={tag} attempt={attempt}/{max_attempts} "
                    f"retryable={retryable}"
                )
                if attempt >= max_attempts or not retryable:
                    raise
                time.sleep(min(10 * attempt, 30))
        if last_exc is not None:
            raise last_exc

    def _build_error_text(self, exc: Exception) -> str:
        """Extract a compact text form of Docker build failures for retry classification."""
        text = str(exc)
        build_log = getattr(exc, "build_log", None)
        if not build_log:
            return text

        parts: list[str] = []
        for chunk in build_log:
            if isinstance(chunk, dict):
                stream = chunk.get("stream")
                if stream:
                    parts.append(stream)
                error = chunk.get("error")
                if error:
                    parts.append(error)
        if parts:
            text = f"{text}\n{''.join(parts)}"
        return text

    def _is_retryable_build_error(self, message: str) -> bool:
        lowered = message.lower()
        retryable_markers = (
            "read timed out",
            "connection reset by peer",
            "connection aborted",
            "temporary failure",
            "temporary failure resolving",
            "failed to connect",
            "failed to fetch",
            "some index files failed to download",
            "bad request",
            "returned a non-zero code: 100",
            "returned a non-zero code: 124",
            "tls handshake timeout",
            "unexpected eof",
            "i/o timeout",
            "network timed out",
            "connection timed out",
            "could not connect",
            "connection broken",
            "incompleteread",
            "protocolerror",
        )
        return any(marker in lowered for marker in retryable_markers)

    def _should_retry_without_build_network(self, exc: Exception) -> bool:
        lowered = str(exc).lower()
        unsupported_markers = (
            "network mode",
            "invalid network mode",
            "unknown network",
            "not supported",
            "host network",
        )
        return any(marker in lowered for marker in unsupported_markers)

    def _truncate_build_error(self, exc: Exception, limit: int = 240) -> str:
        """Keep build failures compact in debug logs."""
        text = " ".join(self._build_error_text(exc).split())
        if len(text) <= limit:
            return text
        return text[: limit - 3] + "..."

    def _rewrite_dockerfile_for_resilient_builds(
        self,
        dockerfile_text: str,
        build_timeout_seconds: Optional[int] = None,
    ) -> str:
        """Inject pip timeout defaults into task Dockerfiles without mutating benchmark data."""
        lines = dockerfile_text.splitlines()
        pip_env_lines = self._pip_env_block().strip().splitlines()
        insert_at = next(
            (index + 1 for index, line in enumerate(lines) if line.strip().upper().startswith("FROM ")),
            0,
        )
        for env_line in reversed(pip_env_lines):
            if env_line not in lines:
                lines.insert(insert_at, env_line)

        rewritten = "\n".join(lines)
        pip_flags = self._pip_install_flags()
        rewritten = re.sub(
            r"\bpip3 install\b(?![^\n]*--timeout)",
            f"pip3 install {pip_flags}",
            rewritten,
        )
        rewritten = re.sub(
            r"\bpip install\b(?![^\n]*--timeout)",
            f"pip install {pip_flags}",
            rewritten,
        )
        build_timeout = build_timeout_seconds or self._apt_build_timeout_seconds()
        rewritten = re.sub(
            r"\bapt-get update\b",
            self._apt_update_command(build_timeout),
            rewritten,
        )
        rewritten = re.sub(
            r"\bapt-get install -y --no-install-recommends\b",
            f"timeout {build_timeout}s apt-get {self._apt_install_options()} install -y --no-install-recommends",
            rewritten,
        )
        rewritten = re.sub(
            r"\bapt-get install -y\b(?![^\n]*--no-install-recommends)",
            f"timeout {build_timeout}s apt-get {self._apt_install_options()} install -y --no-install-recommends",
            rewritten,
        )
        return rewritten + ("\n" if dockerfile_text.endswith("\n") else "")

    def _apt_runtime_timeout_seconds(self) -> int:
        """Keep runtime/test bootstrap bounded so dead mirrors do not hang forever."""
        return 180

    def _apt_build_timeout_seconds(self) -> int:
        """Allow colder first-time image builds to finish after Docker cache resets."""
        return 300

    def _task_build_timeout_seconds(self, task_dir: Path) -> int:
        """Use task-specific build budgets when they are higher than the global floor."""
        task_toml = task_dir / "task.toml"
        configured_timeout = 0.0
        if task_toml.exists():
            try:
                import tomllib

                task_config = tomllib.loads(task_toml.read_text())
                configured_timeout = float(
                    task_config.get("environment", {}).get("build_timeout_sec", 0.0) or 0.0
                )
            except Exception:
                configured_timeout = 0.0
        return max(self._apt_build_timeout_seconds(), int(configured_timeout or 0))

    def _apt_get_options(self) -> str:
        """Return apt transport options tuned for flaky mirror connectivity."""
        return (
            "-o Acquire::Retries=5 "
            "-o Acquire::http::Timeout=30 "
            "-o Acquire::https::Timeout=30 "
            "-o Acquire::ForceIPv4=true"
        )

    def _apt_install_options(self) -> str:
        """Return apt install options with the same transport hardening."""
        return self._apt_get_options()

    def _apt_update_command(self, timeout_seconds: int | None = None) -> str:
        """Return a shell-capped apt update command."""
        timeout_seconds = timeout_seconds or self._apt_runtime_timeout_seconds()
        return f"timeout {int(timeout_seconds)}s apt-get {self._apt_get_options()} update"

    def _apt_install_command(self, packages: str, timeout_seconds: int | None = None) -> str:
        """Return a shell-capped apt install command."""
        timeout_seconds = timeout_seconds or self._apt_runtime_timeout_seconds()
        return (
            f"timeout {int(timeout_seconds)}s apt-get {self._apt_install_options()} "
            f"install -y --no-install-recommends {packages}"
        )

    def _pip_env_block(self) -> str:
        return (
            "ENV PIP_DEFAULT_TIMEOUT=180\n"
            "ENV PIP_RETRIES=8\n"
            "ENV PIP_PROGRESS_BAR=off\n"
            "ENV PIP_DISABLE_PIP_VERSION_CHECK=1\n"
        )

    def _pip_install_flags(self) -> str:
        return "--timeout 180 --retries 8 --progress-bar off"

    def _pip_install_command(
        self,
        executable: str,
        packages: str,
        break_system_packages: bool = False,
    ) -> str:
        parts = [executable, "install"]
        if break_system_packages:
            parts.append("--break-system-packages")
        parts.extend(self._pip_install_flags().split())
        parts.append(packages)
        return " ".join(parts)

    def _run_agent(
        self,
        task_id: str,
        container,
        instruction: str,
        skill: Optional[SkillBundle],
        output_path: str,
        timeout: int,
        include_task_local_skills: bool = True,
    ):
        """Run host-side Codex and let it operate on the task container via docker exec/cp."""
        from ..agent_config import get_agent_params

        exec_cfg = get_agent_params("execution")
        execution_plan = self._build_execution_plan(
            task_id=task_id,
            configured_model=exec_cfg.get("model", "auto"),
            instruction=instruction,
            skill=skill,
            output_path=output_path,
        )
        model = execution_plan.preferred_model
        reasoning_effort = self._resolve_codex_reasoning_effort(model)
        self._log(
            f"agent task={task_id} model={model} difficulty={execution_plan.difficulty.value} "
            f"reason={' | '.join(execution_plan.reasons)}"
        )
        cli_path = exec_cfg.get("cli_path", "/usr/local/bin/codex")
        timeout_sec = min(timeout, exec_cfg.get("timeout", 600))
        with tempfile.TemporaryDirectory(prefix="masterskill-host-exec-") as tmpdir:
            workspace = Path(tmpdir)
            activity_log_path = workspace / "agent-activity.log"
            failure_class: str = ""
            self._prepare_host_exec_workspace(
                workspace,
                container,
                task_id,
                skill,
                include_task_local_skills=include_task_local_skills,
                activity_log_path=activity_log_path,
            )
            prompt = self._build_prompt(
                instruction,
                skill,
                output_path,
                available_skill_paths=self._available_skill_paths(
                    task_id,
                    skill,
                    include_task_local_skills=include_task_local_skills,
                ),
            )
            last_message_path = workspace / "last-message.txt"
            cmd = [
                cli_path,
                "exec",
                "--ephemeral",
                "--json",
                "--dangerously-bypass-approvals-and-sandbox",
                "--skip-git-repo-check",
                "-C",
                str(workspace),
                "-c",
                f'model_reasoning_effort="{reasoning_effort}"',
                "-m",
                model,
                "-o",
                str(last_message_path),
                prompt,
            ]
            started_at = time.monotonic()
            stall_timeout_sec = min(timeout_sec, exec_cfg.get("stall_timeout", 240))
            try:
                self._log(f"codex exec start task={task_id}")
                stdout_path = workspace / "codex-stdout.log"
                stderr_path = workspace / "codex-stderr.log"
                timed_out = False
                stalled = False
                with stdout_path.open("w+", encoding="utf-8") as stdout_handle, stderr_path.open(
                    "w+", encoding="utf-8"
                ) as stderr_handle:
                    proc = subprocess.Popen(
                        cmd,
                        stdout=stdout_handle,
                        stderr=stderr_handle,
                        text=True,
                    )
                    last_activity = started_at
                    latest_mtime = self._latest_workspace_activity_mtime(
                        workspace,
                        activity_log_path=activity_log_path,
                        last_message_path=last_message_path,
                        codex_stdout_path=stdout_path,
                        codex_stderr_path=stderr_path,
                    )
                while proc.poll() is None:
                    now = time.monotonic()
                    current_mtime = self._latest_workspace_activity_mtime(
                        workspace,
                        activity_log_path=activity_log_path,
                        last_message_path=last_message_path,
                        codex_stdout_path=stdout_path,
                        codex_stderr_path=stderr_path,
                    )
                    if current_mtime > latest_mtime:
                        latest_mtime = current_mtime
                        last_activity = now
                    if now - started_at > timeout_sec + 60:
                        timed_out = True
                        proc.kill()
                        break
                    if stall_timeout_sec > 0 and now - last_activity > stall_timeout_sec:
                        stalled = True
                        proc.kill()
                        break
                    time.sleep(5)
                try:
                    result = proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    result = proc.wait(timeout=15)
                stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
                stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
                if stalled:
                    output, input_tokens, cached_input_tokens, output_tokens = self._summarize_codex_json_output(
                        stdout=stdout,
                        stderr=stderr,
                        last_message_path=last_message_path,
                    )
                    output = (
                        f"{output}\nExecution stalled with no observable workspace activity."
                        if output
                        else "Execution stalled with no observable workspace activity."
                    )
                    failure_class = "stall"
                    exit_code = 124
                    self._log(f"codex exec stalled task={task_id}")
                elif timed_out:
                    output, input_tokens, cached_input_tokens, output_tokens = self._summarize_codex_json_output(
                        stdout=stdout,
                        stderr=stderr,
                        last_message_path=last_message_path,
                    )
                    output = f"{output}\nExecution timed out." if output else "Execution timed out."
                    failure_class = "timeout"
                    exit_code = 124
                    self._log(f"codex exec timed out task={task_id}")
                else:
                    output, input_tokens, cached_input_tokens, output_tokens = self._summarize_codex_json_output(
                        stdout=stdout,
                        stderr=stderr,
                        last_message_path=last_message_path,
                    )
                    failure_class = ""
                    exit_code = result
                    self._log(f"codex exec finished task={task_id} exit_code={exit_code}")
            except subprocess.TimeoutExpired as exc:
                timeout_stdout = exc.stdout or ""
                timeout_stderr = exc.stderr or ""
                if isinstance(timeout_stdout, bytes):
                    timeout_stdout = timeout_stdout.decode("utf-8", errors="replace")
                if isinstance(timeout_stderr, bytes):
                    timeout_stderr = timeout_stderr.decode("utf-8", errors="replace")
                output, input_tokens, cached_input_tokens, output_tokens = self._summarize_codex_json_output(
                    stdout=timeout_stdout,
                    stderr=timeout_stderr,
                    last_message_path=last_message_path,
                )
                output = f"{output}\nExecution timed out." if output else "Execution timed out."
                failure_class = "timeout"
                exit_code = 124
                self._log(f"codex exec timed out task={task_id}")
            duration_seconds = time.monotonic() - started_at
            return SimpleNamespace(
                output=output.encode("utf-8", errors="replace"),
                exit_code=exit_code,
                model=model,
                reasoning_effort=reasoning_effort,
                duration_seconds=duration_seconds,
                difficulty=execution_plan.difficulty.value,
                routing_reason="; ".join(execution_plan.reasons),
                input_tokens=input_tokens,
                cached_input_tokens=cached_input_tokens,
                output_tokens=output_tokens,
                failure_class=failure_class,
            )

    def _summarize_codex_json_output(
        self,
        stdout: str,
        stderr: str,
        last_message_path: Path,
    ) -> tuple[str, int, int, int]:
        """Turn Codex JSONL output into a compact execution summary plus usage metrics."""
        text_messages: list[str] = []
        non_json_lines: list[str] = []
        input_tokens = 0
        cached_input_tokens = 0
        output_tokens = 0

        for raw_line in stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                non_json_lines.append(raw_line)
                continue

            event_type = event.get("type", "")
            if event_type == "item.completed":
                item = event.get("item", {})
                if item.get("type") == "agent_message":
                    text = str(item.get("text", "")).strip()
                    if text:
                        text_messages.append(text)
            elif event_type == "turn.completed":
                usage = event.get("usage", {}) or {}
                input_tokens = int(usage.get("input_tokens", 0) or 0)
                cached_input_tokens = int(usage.get("cached_input_tokens", 0) or 0)
                output_tokens = int(usage.get("output_tokens", 0) or 0)

        if last_message_path.exists():
            last_message = last_message_path.read_text().strip()
            if last_message and (not text_messages or text_messages[-1] != last_message):
                text_messages.append(last_message)

        output_parts: list[str] = []
        if text_messages:
            output_parts.append("\n\n".join(text_messages))
        if non_json_lines:
            output_parts.append("\n".join(non_json_lines))
        if stderr.strip():
            output_parts.append(stderr.strip())
        if input_tokens or cached_input_tokens or output_tokens:
            output_parts.append(
                "[Usage]\n"
                f"input_tokens={input_tokens}\n"
                f"cached_input_tokens={cached_input_tokens}\n"
                f"output_tokens={output_tokens}"
            )

        return "\n\n".join(part for part in output_parts if part), input_tokens, cached_input_tokens, output_tokens

    def _build_prompt(
        self,
        instruction: str,
        skill: Optional[SkillBundle],
        output_path: str,
        available_skill_paths: Optional[list[str]] = None,
    ) -> str:
        skill_note = ""
        if available_skill_paths:
            listed = "\n".join(f"- {path}" for path in available_skill_paths[:12])
            candidate_note = ""
            if skill is not None:
                candidate_note = (
                    f"The candidate skill currently under evaluation is ./skills/{skill.skill_id}/SKILL.md. "
                    "Read and apply it first. Use other bundled task-local skills only as supporting references when they materially help the candidate skill pass the official test.\n"
                )
            skill_note = (
                "\nRelevant skills are available locally and inside the task container.\n"
                f"{candidate_note}"
                "Read the ones that matter before implementing changes, and combine bundled task-local skills when useful.\n"
                f"{listed}\n"
            )
        elif skill is not None:
            skill_note = (
                f"\nA skill is available locally at ./skills/{skill.skill_id}/SKILL.md. "
                "A copy is also already inside the task container.\n"
            )

        output_note = (
            f"\nWrite the final artifact to {output_path} inside the task container.\n"
            if output_path
            else "\nFollow the task instruction exactly and write outputs to the paths it specifies inside the task container.\n"
        )

        return (
            "You are solving a SkillsBench task using helper scripts that control a running Docker container.\n"
            "For any command that must run in the task environment, use ./task_shell \"<command>\".\n"
            "To copy files into the container, use ./task_put <local_path> <container_path>.\n"
            "To copy files out of the container, use ./task_get <container_path> <local_path>.\n"
            "Assume the task image may only have basic Unix tools plus python3; prefer python3 over python and grep/find/sed over rg.\n"
            "Treat bundled task-local skills under ./skills as read-only references. Do not edit those bundled files in place.\n"
            "You may still create derived helpers elsewhere in the workspace, and you may iterate on non-bundled candidate skills the system generated for this run.\n"
            "If a bundled skill already contains an end-to-end script or pipeline, use it before inventing a new approach.\n"
            "When a bundled skill ships runnable files under scripts/ or a pipeline.py, first copy that skill directory to a derived workspace path outside ./skills, make only the minimum runtime adjustments there, and run the derived copy.\n"
            "Use ./clone_skill ./skills/<skill-dir> ./derived_<skill-dir> when you need a writable derived copy of a bundled skill.\n"
            "Do not start from scratch while a bundled pipeline is available but untried.\n"
            "Never write console progress logs into required output artifact paths. Keep logs on stdout or temp files, and write final CSV/JSON outputs cleanly and atomically.\n"
            "Once the required output files are written and a minimal sanity check confirms they exist and look plausible, stop immediately.\n"
            "Do not keep researching or polishing after the required artifacts are ready.\n"
            "Read the instruction carefully, inspect local files as needed, and complete the task.\n"
            f"{skill_note}"
            f"{output_note}"
            "Task instruction:\n"
            f"{instruction}\n"
        )

    def _write_instruction(self, container, instruction: str) -> None:
        container.put_archive("/root", self._make_tar_content("instruction.md", instruction))

    def _copy_task_local_skills(self, container, task_id: str) -> None:
        """Expose bundled task-local skills during skill-guided execution."""
        skill_dirs = self._task_local_skill_dirs(task_id)
        if not skill_dirs:
            return

        container.exec_run(["bash", "-lc", "mkdir -p /root/.claude/skills /root/.codex/skills /root/.skills"])
        for skill_dir in skill_dirs:
            payload = self._make_tar_from_disk(skill_dir, arcname=skill_dir.name)
            container.put_archive("/root/.claude/skills", payload)
            container.put_archive("/root/.codex/skills", payload)
            container.put_archive("/root/.skills", payload)

    def _copy_skill(self, container, skill: SkillBundle) -> None:
        container.exec_run(["bash", "-lc", "mkdir -p /root/.claude/skills /root/.codex/skills /root/.skills"])
        entries = {f"{skill.skill_id}/SKILL.md": skill.to_skill_md()}
        for relative_path, script_content in self._expand_skill_support_files(skill).items():
            entries[f"{skill.skill_id}/{relative_path}"] = script_content
        payload = self._make_tar_tree(entries)
        container.put_archive("/root/.claude/skills", payload)
        container.put_archive("/root/.codex/skills", payload)
        container.put_archive("/root/.skills", payload)

    def _copy_tests(self, container, task_dir: Path) -> None:
        tests_dir = task_dir / "tests"
        container.exec_run(["bash", "-lc", "mkdir -p /tests"])
        with tempfile.TemporaryDirectory(prefix=f"masterskill-tests-{task_dir.name}-") as tmpdir:
            workspace = Path(tmpdir) / "tests"
            shutil.copytree(tests_dir, workspace)
            test_script = workspace / "test.sh"
            if test_script.exists():
                test_script.write_text(
                    self._rewrite_shell_script_for_resilience(test_script.read_text())
                )
            container.put_archive("/tests", self._make_tar_from_disk(workspace, arcname="."))

    def _rewrite_shell_script_for_resilience(self, script_text: str) -> str:
        """Harden verifier shell scripts without mutating benchmark fixtures."""
        runtime_timeout = self._apt_runtime_timeout_seconds()
        rewritten = re.sub(
            r"\bpip3 install\b(?![^\n]*--timeout)",
            f"pip3 install {self._pip_install_flags()}",
            script_text,
        )
        rewritten = re.sub(
            r"\bpip install\b(?![^\n]*--timeout)",
            f"pip install {self._pip_install_flags()}",
            rewritten,
        )
        rewritten = re.sub(
            r"\bapt-get update\b",
            self._apt_update_command(runtime_timeout),
            rewritten,
        )
        rewritten = re.sub(
            r"\bapt-get install -y --no-install-recommends\b",
            f"timeout {runtime_timeout}s apt-get {self._apt_install_options()} install -y --no-install-recommends",
            rewritten,
        )
        rewritten = re.sub(
            r"\bapt-get install -y\b(?![^\n]*--no-install-recommends)",
            f"timeout {runtime_timeout}s apt-get {self._apt_install_options()} install -y --no-install-recommends",
            rewritten,
        )
        return rewritten

    def _run_tests(self, container, timeout: int):
        has_test_script = self._decode_output(
            container.exec_run(
                ["bash", "-lc", "if [ -f /tests/test.sh ]; then echo yes; else echo no; fi"],
                demux=False,
                stream=False,
                tty=False,
                environment={},
            ).output
        ).strip() == "yes"
        if has_test_script:
            self._log("running task test.sh")
            needs_uvx = self._decode_output(
                container.exec_run(
                    ["bash", "-lc", "if grep -q 'uvx' /tests/test.sh; then echo yes; else echo no; fi"],
                    demux=False,
                    stream=False,
                    tty=False,
                    environment={},
                ).output
            ).strip() == "yes"
            uv_bootstrap = ""
            if needs_uvx:
                uv_bootstrap = (
                    "if ! command -v uvx >/dev/null 2>&1; then "
                    "if command -v pip3 >/dev/null 2>&1; then "
                    "pip3 install --break-system-packages uv || pip3 install uv || true; "
                    "fi; "
                    "fi && "
                )
            test_cmd = (
                "chmod +x /tests/test.sh && " +
                uv_bootstrap +
                f"timeout {int(timeout)}s /tests/test.sh 2>&1"
            )
            return container.exec_run(
                ["bash", "-lc", test_cmd],
                demux=False,
                stream=False,
                tty=False,
                environment={},
            )
        self._log("running pytest fallback")
        return container.exec_run(
            ["bash", "-lc", f"timeout {int(timeout)}s python3 -m pytest /tests/test_outputs.py -v 2>&1"],
            demux=False,
            stream=False,
            tty=False,
            environment={},
        )

    def _materialize_execution_artifacts(self, container) -> list[tuple[str, bytes]]:
        """Export changed task artifacts for fresh-container evaluation.

        The execution container is considered untrusted after model execution.
        Only file/dir changes under task-typical writable roots are restored into
        a clean evaluation container; tests and solution assets are never copied.
        """
        artifacts: list[tuple[str, bytes]] = []
        for path in self._select_changed_paths(container):
            try:
                stream, _ = container.get_archive(path)
            except Exception as exc:
                self._log(f"skip artifact path={path} reason={exc}")
                continue
            payload = b"".join(stream)
            artifacts.append((path, payload))
        self._log(
            "execution artifacts exported="
            + (", ".join(path for path, _ in artifacts) if artifacts else "none")
        )
        return artifacts

    def _restore_execution_artifacts(self, container, artifacts: list[tuple[str, bytes]]) -> None:
        """Restore exported task artifacts into a clean evaluation container."""
        for path, payload in artifacts:
            parent = str(Path(path).parent)
            if parent and parent != "/":
                container.exec_run(["bash", "-lc", f"mkdir -p {shlex.quote(parent)}"])
            container.put_archive(parent if parent else "/", payload)

    def _select_changed_paths(self, container) -> list[str]:
        """Choose task-relevant changed paths while excluding evaluation assets."""
        try:
            diff_entries = container.diff()
        except Exception as exc:
            self._log(f"container diff failed: {exc}")
            return []

        candidate_paths: list[str] = []
        for entry in diff_entries:
            path = entry.get("Path") or ""
            kind = entry.get("Kind")
            normalized = self._normalize_container_path(path)
            if not normalized:
                continue
            if kind == 2:
                continue
            if not self._is_exportable_artifact_path(normalized):
                continue
            candidate_paths.append(normalized)

        selected: list[str] = []
        for path in sorted(set(candidate_paths), key=lambda value: (len(value), value), reverse=True):
            prefix = path.rstrip("/") + "/"
            if any(existing.startswith(prefix) for existing in selected):
                continue
            selected.append(path)
        selected.sort()
        return selected

    def _normalize_container_path(self, path: str) -> str:
        if not path:
            return ""
        normalized = path.replace("\\", "/")
        if not normalized.startswith("/"):
            normalized = "/" + normalized
        while "//" in normalized:
            normalized = normalized.replace("//", "/")
        return normalized.rstrip("/") or "/"

    def _is_exportable_artifact_path(self, path: str) -> bool:
        protected_prefixes = (
            "/tests",
            "/solution",
            "/root/.claude",
            "/root/.codex",
            "/root/.skills",
            "/root/.cache",
            "/root/.npm",
            "/tmp/.cache",
        )
        safe_roots = (
            "/root",
            "/tmp",
            "/workspace",
            "/work",
            "/app",
            "/project",
            "/output",
            "/results",
            "/home",
        )
        if path in safe_roots:
            return False
        if self._is_cache_path(path):
            return False
        if any(path == prefix or path.startswith(prefix + "/") for prefix in protected_prefixes):
            return False
        return any(path.startswith(root + "/") for root in safe_roots)

    def _is_cache_path(self, path: str) -> bool:
        """Filter cache trees that can be huge or unstable to archive."""
        normalized = self._normalize_container_path(path)
        transient_prefixes = (
            "/tmp/tsx-",
            "/tmp/v8-compile-cache-",
            "/tmp/playwright-download-",
        )
        if any(normalized == prefix or normalized.startswith(prefix) for prefix in transient_prefixes):
            return True
        if "/.next/cache/" in normalized:
            return True
        if normalized.startswith("/home/"):
            parts = normalized.split("/")
            if len(parts) >= 4 and parts[3] == ".cache":
                return True
        cache_markers = (
            "/.cache/",
            "/huggingface/",
            "/pip/",
            "/npm/",
        )
        if any(marker in normalized for marker in cache_markers):
            parent = normalized.rsplit("/", 1)[0]
            if parent.endswith(".cache") or "/.cache/" in normalized:
                return True
        return False

    def _is_text_preview_path(self, path: str) -> bool:
        """Return whether a path should be previewed as text."""
        lowered = path.lower()
        text_extensions = (
            ".txt", ".md", ".json", ".jsonl", ".csv", ".tsv", ".rttm", ".ass",
            ".yaml", ".yml", ".xml", ".html", ".log", ".py", ".sh",
        )
        return lowered.endswith(text_extensions)

    def _truncate_artifact_preview(self, content: str, limit: int = 1600) -> str:
        """Keep artifact previews compact enough for Judger prompts."""
        normalized = content.strip()
        if not normalized:
            return ""
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3] + "..."

    def _is_directory(self, container, path: str) -> bool:
        result = container.exec_run(
            ["bash", "-lc", f"if [ -d {shlex.quote(path)} ]; then echo yes; else echo no; fi"],
            demux=False,
            stream=False,
            tty=False,
            environment={},
        )
        return self._decode_output(result.output).strip() == "yes"

    def _list_directory_preview(self, container, path: str) -> str:
        result = container.exec_run(
            [
                "bash",
                "-lc",
                f"find {shlex.quote(path)} -maxdepth 2 -type f | sort | head -n 20",
            ],
            demux=False,
            stream=False,
            tty=False,
            environment={},
        )
        if result.exit_code != 0:
            return ""
        return self._decode_output(result.output).strip()

    def _stat_summary(self, container, path: str) -> str:
        result = container.exec_run(
            [
                "bash",
                "-lc",
                f"if [ -e {shlex.quote(path)} ]; then stat -c '%F, %s bytes' {shlex.quote(path)}; fi",
            ],
            demux=False,
            stream=False,
            tty=False,
            environment={},
        )
        if result.exit_code != 0:
            return ""
        return self._decode_output(result.output).strip()

    def _build_artifact_report(self, container, output_path: str = "") -> str:
        """Summarize changed artifacts and preview text outputs for the Judger."""
        candidate_paths: list[str] = []
        if output_path:
            candidate_paths.append(self._normalize_container_path(output_path))
        candidate_paths.extend(self._select_changed_paths(container))

        seen: set[str] = set()
        ordered_paths: list[str] = []
        for path in candidate_paths:
            normalized = self._normalize_container_path(path)
            if not normalized or normalized in seen:
                continue
            ordered_paths.append(normalized)
            seen.add(normalized)

        if not ordered_paths:
            return ""

        sections: list[str] = []
        for path in ordered_paths[:12]:
            if self._is_directory(container, path):
                listing = self._list_directory_preview(container, path)
                section = f"- {path}/"
                if listing:
                    section += f"\n{listing}"
                sections.append(section)
                continue

            if self._is_text_preview_path(path):
                preview = self._truncate_artifact_preview(self._get_file(container, path))
                if preview:
                    sections.append(f"- {path}\n```text\n{preview}\n```")
                    continue

            stat_summary = self._stat_summary(container, path)
            sections.append(f"- {path}{f' ({stat_summary})' if stat_summary else ''}")

        return "\n".join(sections)

    def _prepare_host_exec_workspace(
        self,
        workspace: Path,
        container,
        task_id: str,
        skill: Optional[SkillBundle],
        include_task_local_skills: bool = True,
        activity_log_path: Optional[Path] = None,
    ) -> None:
        workspace.mkdir(parents=True, exist_ok=True)
        activity_log = shlex.quote(str(activity_log_path or (workspace / "agent-activity.log")))
        bundled_skill_names = [skill_dir.name for skill_dir in self._task_local_skill_dirs(task_id)]
        bundled_roots_literal = " ".join(shlex.quote(f"skills/{name}") for name in bundled_skill_names)
        self._write_workspace_file(
            workspace / "task_shell",
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            f"printf '%s task_shell %s\\n' \"$(date -Is)\" \"$*\" >> {activity_log}\n"
            f"docker exec {shlex.quote(container.id)} bash -lc \"$*\"\n",
            executable=True,
        )
        self._write_workspace_file(
            workspace / "task_put",
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "src=\"${1#./}\"\n"
            f"for root in {bundled_roots_literal}; do\n"
            "  if [[ -n \"$root\" && ( \"$src\" == \"$root\" || \"$src\" == \"$root\"/* ) ]]; then\n"
            "    echo 'Refusing to overwrite bundled task-local skill files; create a derived helper or candidate skill instead.' >&2\n"
            "    exit 2\n"
            "  fi\n"
            "done\n"
            f"printf '%s task_put %s -> %s\\n' \"$(date -Is)\" \"$1\" \"$2\" >> {activity_log}\n"
            f"docker cp \"$1\" {shlex.quote(container.id)}:\"$2\"\n",
            executable=True,
        )
        self._write_workspace_file(
            workspace / "task_get",
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            f"printf '%s task_get %s -> %s\\n' \"$(date -Is)\" \"$1\" \"$2\" >> {activity_log}\n"
            f"docker cp {shlex.quote(container.id)}:\"$1\" \"$2\"\n",
            executable=True,
        )
        self._write_workspace_file(
            workspace / "README.md",
            "Use `./task_shell` to run commands inside the task container.\n"
            "Use `./task_put` and `./task_get` to move files across the container boundary.\n",
        )
        self._write_workspace_file(
            workspace / "clone_skill",
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "src=\"${1:?source skill dir required}\"\n"
            "dst=\"${2:?destination dir required}\"\n"
            "rm -rf \"$dst\"\n"
            "cp -R \"$src\" \"$dst\"\n"
            "find \"$dst\" -type d -exec chmod 755 {} +\n"
            "find \"$dst\" -type f -exec chmod 644 {} +\n",
            executable=True,
        )
        if include_task_local_skills:
            for skill_dir in self._task_local_skill_dirs(task_id):
                shutil.copytree(skill_dir, workspace / "skills" / skill_dir.name, dirs_exist_ok=True)
                self._make_tree_read_only(workspace / "skills" / skill_dir.name)
        if skill is not None and skill.skill_id not in {path.name for path in self._task_local_skill_dirs(task_id)}:
            skill_root = workspace / "skills" / skill.skill_id
            self._write_workspace_file(skill_root / "SKILL.md", skill.to_skill_md())
            for relative_path, script_content in self._expand_skill_support_files(skill).items():
                self._write_workspace_file(skill_root / relative_path, script_content)

    def _task_local_skill_dirs(self, task_id: str) -> list[Path]:
        """Return bundled task-local skill directories."""
        skills_root = resolve_task_dir(self.skillsbench_root, task_id) / "environment" / "skills"
        if not skills_root.exists():
            return []
        return sorted(path for path in skills_root.iterdir() if path.is_dir())

    def _available_skill_paths(
        self,
        task_id: str,
        skill: Optional[SkillBundle],
        include_task_local_skills: bool = True,
    ) -> list[str]:
        """List skill entry points visible to the execution agent."""
        paths = []
        if include_task_local_skills:
            for path in self._task_local_skill_dirs(task_id):
                paths.append(f"./skills/{path.name}/SKILL.md")
                pipeline_path = path / "scripts" / "pipeline.py"
                if pipeline_path.exists():
                    paths.append(f"./skills/{path.name}/scripts/pipeline.py")
                for script_path in sorted((path / "scripts").glob("*.py"))[:4]:
                    rendered = f"./skills/{path.name}/scripts/{script_path.name}"
                    if rendered not in paths:
                        paths.append(rendered)
        if skill is not None:
            candidate_path = f"./skills/{skill.skill_id}/SKILL.md"
            if candidate_path not in paths:
                paths.append(candidate_path)
        return paths

    def _write_workspace_file(self, path: Path, content: str, executable: bool = False) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        if executable:
            path.chmod(0o755)

    def _make_tree_read_only(self, root: Path) -> None:
        """Keep bundled skills immutable during execution runs."""
        if not root.exists():
            return
        for path in sorted(root.rglob("*"), reverse=True):
            if path.is_dir():
                path.chmod(0o555)
            elif path.is_file():
                path.chmod(0o444)
        root.chmod(0o555)

    def _latest_workspace_activity_mtime(
        self,
        workspace: Path,
        activity_log_path: Path,
        last_message_path: Path,
        codex_stdout_path: Path,
        codex_stderr_path: Path,
    ) -> float:
        """Track whether the agent is actually doing work inside the workspace."""
        latest = 0.0
        for candidate in (activity_log_path, last_message_path, codex_stdout_path, codex_stderr_path):
            if candidate.exists():
                latest = max(latest, candidate.stat().st_mtime)
        local_app = workspace / "local_app"
        if local_app.exists():
            for path in local_app.rglob("*"):
                if path.is_file():
                    latest = max(latest, path.stat().st_mtime)
        return latest

    def _expand_skill_support_files(self, skill: SkillBundle) -> dict[str, str]:
        """Normalize skill support files and preserve a legacy scripts/ alias."""
        files: dict[str, str] = {}
        for relative_path, content in skill.scripts.items():
            normalized = relative_path.strip().lstrip("/").replace("\\", "/")
            if not normalized:
                continue
            files[normalized] = content
            if "/" not in normalized:
                files.setdefault(f"scripts/{normalized}", content)
        return files

    def _get_image(self, image_name: str):
        """Return an image by name if it exists."""
        try:
            return self.client.images.get(image_name)
        except Exception:
            return None

    def _hash_tree(self, root: Path) -> str:
        """Hash non-skill environment files for base-image reuse.

        Task-local skills are mounted into the execution container at runtime, so
        iterating on `environment/skills` should not invalidate the base image.
        """
        digest = hashlib.sha256()
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            if self._is_skill_tree_path(root, path):
                continue
            digest.update(str(path.relative_to(root)).encode("utf-8"))
            digest.update(path.read_bytes())
        return digest.hexdigest()

    def _can_reuse_existing_image_for_skill_only_changes(self, image, context_root: Path) -> bool:
        """Reuse an existing image when only task-local skill files changed.

        Older images do not have the reduced hash label, so fall back to comparing
        the image creation time against the latest non-skill environment change.
        """
        created_raw = image.attrs.get("Created")
        if not created_raw:
            return False
        try:
            created_at = datetime.fromisoformat(created_raw.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return False
        latest_non_skill_change = 0.0
        for path in context_root.rglob("*"):
            if not path.is_file():
                continue
            if self._is_skill_tree_path(context_root, path):
                continue
            latest_non_skill_change = max(latest_non_skill_change, path.stat().st_mtime)
        return latest_non_skill_change > 0 and created_at >= latest_non_skill_change

    def _is_skill_tree_path(self, root: Path, path: Path) -> bool:
        """Return whether a file lives under the task-local skills subtree."""
        relative_parts = path.relative_to(root).parts
        return bool(relative_parts) and relative_parts[0] == "skills"

    def _make_tar_from_disk(self, source_path: Path, arcname: str) -> bytes:
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
            tar.add(str(source_path), arcname=arcname)
        return tar_buffer.getvalue()

    def _make_tar_tree(self, files: dict[str, str]) -> bytes:
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
            for name, content in files.items():
                data = content.encode()
                info = tarfile.TarInfo(name=name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
        return tar_buffer.getvalue()

    def _make_tar_content(self, filename: str, content: str) -> bytes:
        """Create a tar archive with a single file."""
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
            info = tarfile.TarInfo(name=filename)
            info.size = len(content.encode())
            tar.addfile(info, io.BytesIO(content.encode()))
        return tar_buffer.getvalue()

    def _get_file(self, container, path: str) -> str:
        """Get file content from container."""
        try:
            bits, stat = container.get_archive(path)
            if not bits:
                return ""

            import tarfile
            import io

            tar_buffer = io.BytesIO()
            for chunk in bits:
                tar_buffer.write(chunk)

            tar_buffer.seek(0)
            with tarfile.open(fileobj=tar_buffer) as tar:
                member = tar.getmember(os.path.basename(path))
                f = tar.extractfile(member)
                return f.read().decode("utf-8") if f else ""
        except:
            return ""

    def _decode_output(self, output: bytes | tuple | None) -> str:
        if output is None:
            return ""
        if isinstance(output, tuple):
            joined = b"".join(part for part in output if part)
            return joined.decode("utf-8", errors="replace")
        if isinstance(output, bytes):
            return output.decode("utf-8", errors="replace")
        return str(output)

    def _get_execution_env(self) -> dict[str, str]:
        """Retained for compatibility; execution now uses host Codex directly."""
        return {}

    def _resolve_codex_reasoning_effort(self, model: str) -> str:
        """Select a reasoning effort compatible with the chosen model."""
        lowered = model.lower()
        if "5.1" in lowered:
            return "high"
        if "5.2" in lowered:
            return "medium"
        if "5.3" in lowered:
            return "high"
        if "5.4" in lowered:
            return "high"
        return "medium"

    def _build_execution_plan(
        self,
        task_id: str,
        configured_model: str,
        instruction: str = "",
        skill: Optional[SkillBundle] = None,
        output_path: str = "",
    ):
        """Build an explicit execution plan."""
        plan = self.task_router.build_plan(
            task_id=task_id,
            instruction=instruction,
            output_path=output_path,
            skill=skill,
        )
        if configured_model and configured_model != "auto":
            plan.preferred_model = configured_model
            plan.reasons.append(f"execution config override={configured_model}")
        return plan

    def _classify_failure(self, output: str, exit_code: int, passed: bool) -> str:
        """Classify the main failure type from execution and test logs."""
        if passed:
            return ""

        lowered = output.lower()
        if "execution stalled with no observable workspace activity" in lowered:
            return "stall"
        if exit_code == 124 or "timed out" in lowered:
            return "timeout"
        if "dockerfile not found" in lowered:
            return "missing_dockerfile"
        if "test file not found" in lowered:
            return "missing_test_file"
        if "permission denied" in lowered:
            return "permission_error"
        if "no module named" in lowered or "command not found" in lowered or "uvx" in lowered:
            return "environment_dependency_missing"
        if "assertionerror" in lowered or " failed" in lowered or "traceback" in lowered:
            return "test_failure"
        if exit_code != 0:
            return "execution_failed"
        return "unknown_failure"
