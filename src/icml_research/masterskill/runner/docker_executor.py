"""Docker executor for skill evaluation."""

import json
import os
import io
import shlex
import subprocess
import tarfile
import tempfile
from types import SimpleNamespace
from pathlib import Path
from typing import Optional

try:
    import docker
except ImportError:
    docker = None

from ..core.types import SkillBundle


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
        try:
            self.client = docker.from_env()
        except Exception as exc:
            raise RuntimeError(
                "Docker is not available from this environment. "
                "Install the Docker SDK and ensure the Docker engine is reachable."
            ) from exc

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
                "error": str,           # Error message if any
                "exit_code": int,
            }
        """
        task_dir = self.skillsbench_root / "tasks" / task_id
        if not self._task_has_dockerfile(task_dir):
            return {
                "success": False,
                "output_file": "",
                "execution_log": "",
                "error": f"Dockerfile not found: {task_dir / 'environment' / 'Dockerfile'}",
                "exit_code": -1,
            }

        image_name = f"masterskill:{task_id}"
        self._build_image(task_dir, image_name)

        container = None
        try:
            container = self._start_container(image_name)
            self._write_instruction(container, instruction)
            self._copy_skill(container, skill)

            exec_result = self._run_agent(
                container=container,
                instruction=instruction,
                skill=skill,
                output_path=output_path,
                timeout=timeout,
            )
            execution_log = self._decode_output(exec_result.output)
            artifact_summary = self._summarize_outputs(container)
            combined_log = execution_log
            if artifact_summary:
                combined_log += f"\n\n[Output Artifacts]\n{artifact_summary}"

            return {
                "success": exec_result.exit_code == 0,
                "output_file": self._get_file(container, output_path) if output_path else "",
                "execution_log": combined_log,
                "error": "" if exec_result.exit_code == 0 else "Execution failed",
                "exit_code": exec_result.exit_code,
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
    ) -> dict:
        """Run the official SkillsBench test.

        Returns:
            {
                "passed": bool,
                "score": float,        # 0.0 - 1.0
                "details": str,        # Test output
                "exit_code": int,
            }
        """
        task_dir = self.skillsbench_root / "tasks" / task_id
        test_file = task_dir / "tests" / "test_outputs.py"
        if not test_file.exists():
            return {"passed": False, "score": 0.0, "details": "Test file not found", "exit_code": -1}

        image_name = f"masterskill:{task_id}"
        self._build_image(task_dir, image_name)

        container = None
        try:
            container = self._start_container(image_name)
            self._write_instruction(container, instruction)
            if skill is not None:
                self._copy_skill(container, skill)
            self._copy_tests(container, task_dir)

            exec_result = self._run_agent(
                container=container,
                instruction=instruction,
                skill=skill,
                output_path="",
                timeout=timeout,
            )
            test_result = self._run_tests(container, timeout)

            details = (
                "[Execution Log]\n"
                + self._decode_output(exec_result.output)
                + "\n\n[Test Output]\n"
                + self._decode_output(test_result.output)
            )
            passed = exec_result.exit_code == 0 and test_result.exit_code == 0
            return {
                "passed": passed,
                "score": 1.0 if passed else 0.0,
                "details": details,
                "exit_code": test_result.exit_code,
            }
        finally:
            if container is not None:
                container.remove(force=True)

    def run_task(
        self,
        task_id: str,
        instruction: str,
        output_path: str = "",
        skill_path: Optional[str] = None,
        timeout: int = 900,
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
        )
        return {
            "passed": test_result["passed"],
            "output": "",
            "execution_log": test_result["details"],
            "error": "" if test_result["passed"] else "Model could not solve autonomously",
            "exit_code": test_result["exit_code"],
        }

    def _task_has_dockerfile(self, task_dir: Path) -> bool:
        return (task_dir / "environment" / "Dockerfile").exists()

    def _get_image_name(self, task_id: str) -> str:
        """Get image name for a task."""
        return f"skillsbench:{task_id}"

    def _build_image(self, task_dir: Path, image_name: str) -> None:
        """Build Docker image from Dockerfile."""
        context_path = task_dir / "environment"
        self.client.images.build(
            path=str(context_path),
            dockerfile="Dockerfile",
            tag=image_name,
            rm=True,
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

    def _run_agent(self, container, instruction: str, skill: Optional[SkillBundle], output_path: str, timeout: int):
        """Run host-side Codex and let it operate on the task container via docker exec/cp."""
        from ..agent_config import get_agent_params

        exec_cfg = get_agent_params("execution")
        model = self._resolve_execution_model(
            exec_cfg.get("model", "auto"),
            instruction=instruction,
            skill=skill,
            output_path=output_path,
        )
        reasoning_effort = self._resolve_codex_reasoning_effort(model)
        cli_path = exec_cfg.get("cli_path", "/usr/local/bin/codex")
        timeout_sec = min(timeout, exec_cfg.get("timeout", 600))
        with tempfile.TemporaryDirectory(prefix="masterskill-host-exec-") as tmpdir:
            workspace = Path(tmpdir)
            self._prepare_host_exec_workspace(workspace, container, skill)
            prompt = self._build_prompt(instruction, skill, output_path)
            last_message_path = workspace / "last-message.txt"
            cmd = [
                cli_path,
                "exec",
                "--ephemeral",
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
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec + 60,
                )
                output = result.stdout or ""
                if result.stderr:
                    output = f"{output}\n{result.stderr}" if output else result.stderr
                exit_code = result.returncode
            except subprocess.TimeoutExpired as exc:
                output = exc.stdout or ""
                stderr = exc.stderr or ""
                if isinstance(output, bytes):
                    output = output.decode("utf-8", errors="replace")
                if isinstance(stderr, bytes):
                    stderr = stderr.decode("utf-8", errors="replace")
                if stderr:
                    output = f"{output}\n{stderr}" if output else stderr
                output = f"{output}\nExecution timed out." if output else "Execution timed out."
                exit_code = 124
            if last_message_path.exists():
                last_message = last_message_path.read_text().strip()
                if last_message:
                    output = f"{output}\n\n[Last Message]\n{last_message}" if output else last_message
            return SimpleNamespace(
                output=output.encode("utf-8", errors="replace"),
                exit_code=exit_code,
            )

    def _build_prompt(self, instruction: str, skill: Optional[SkillBundle], output_path: str) -> str:
        skill_note = ""
        if skill is not None:
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
            "Read the instruction carefully, inspect local files as needed, and complete the task.\n"
            f"{skill_note}"
            f"{output_note}"
            "Task instruction:\n"
            f"{instruction}\n"
        )

    def _write_instruction(self, container, instruction: str) -> None:
        container.put_archive("/root", self._make_tar_content("instruction.md", instruction))

    def _copy_skill(self, container, skill: SkillBundle) -> None:
        container.exec_run(["bash", "-lc", "mkdir -p /root/.claude/skills /root/.codex/skills /root/.skills"])
        entries = {f"{skill.skill_id}/SKILL.md": skill.to_skill_md()}
        for script_name, script_content in skill.scripts.items():
            entries[f"{skill.skill_id}/scripts/{script_name}"] = script_content
        payload = self._make_tar_tree(entries)
        container.put_archive("/root/.claude/skills", payload)
        container.put_archive("/root/.codex/skills", payload)
        container.put_archive("/root/.skills", payload)

    def _copy_tests(self, container, task_dir: Path) -> None:
        tests_dir = task_dir / "tests"
        container.exec_run(["bash", "-lc", "mkdir -p /tests"])
        container.put_archive("/tests", self._make_tar_from_disk(tests_dir, arcname="."))

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
            test_cmd = (
                "chmod +x /tests/test.sh && "
                "if ! command -v uvx >/dev/null 2>&1; then "
                "if command -v pip3 >/dev/null 2>&1; then "
                "pip3 install --break-system-packages uv || pip3 install uv || true; "
                "fi; "
                "fi && "
                f"timeout {int(timeout)}s /tests/test.sh 2>&1"
            )
            return container.exec_run(
                ["bash", "-lc", test_cmd],
                demux=False,
                stream=False,
                tty=False,
                environment={},
            )
        return container.exec_run(
            ["bash", "-lc", f"timeout {int(timeout)}s python3 -m pytest /tests/test_outputs.py -v 2>&1"],
            demux=False,
            stream=False,
            tty=False,
            environment={},
        )

    def _summarize_outputs(self, container) -> str:
        result = container.exec_run(
            [
                "bash",
                "-lc",
                "find /root -maxdepth 3 "
                "\\( -path '/root/.claude' -o -path '/root/.skills' -o -path '/root/.codex' \\) -prune "
                "-o -type f -printf '%p\\n' | sort",
            ],
            demux=False,
            stream=False,
            tty=False,
            environment={},
        )
        if result.exit_code != 0:
            return ""
        return self._decode_output(result.output)

    def _prepare_host_exec_workspace(self, workspace: Path, container, skill: Optional[SkillBundle]) -> None:
        workspace.mkdir(parents=True, exist_ok=True)
        self._write_workspace_file(
            workspace / "task_shell",
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            f"docker exec {shlex.quote(container.id)} bash -lc \"$*\"\n",
            executable=True,
        )
        self._write_workspace_file(
            workspace / "task_put",
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            f"docker cp \"$1\" {shlex.quote(container.id)}:\"$2\"\n",
            executable=True,
        )
        self._write_workspace_file(
            workspace / "task_get",
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            f"docker cp {shlex.quote(container.id)}:\"$1\" \"$2\"\n",
            executable=True,
        )
        self._write_workspace_file(
            workspace / "README.md",
            "Use `./task_shell` to run commands inside the task container.\n"
            "Use `./task_put` and `./task_get` to move files across the container boundary.\n",
        )
        if skill is not None:
            skill_root = workspace / "skills" / skill.skill_id
            self._write_workspace_file(skill_root / "SKILL.md", skill.to_skill_md())
            for script_name, script_content in skill.scripts.items():
                self._write_workspace_file(skill_root / "scripts" / script_name, script_content)

    def _write_workspace_file(self, path: Path, content: str, executable: bool = False) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        if executable:
            path.chmod(0o755)

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
        if "5.4" in lowered:
            return "xhigh"
        return "xhigh"

    def _resolve_execution_model(
        self,
        configured_model: str,
        instruction: str = "",
        skill: Optional[SkillBundle] = None,
        output_path: str = "",
    ) -> str:
        """Pick a GPT-5 family model based on task difficulty."""
        if configured_model and configured_model != "auto":
            return configured_model

        text = f"{instruction}\n{output_path}".lower()
        hard_keywords = (
            "optimiz",
            "proof",
            "simulation",
            "crystallographic",
            "quantum",
            "fuzz",
            "compiler",
            "video",
            "planning",
            "adjacency",
            "power-flow",
            "docking",
            "citation",
            "bibtex",
            "bibliograph",
            "hallucinated citation",
        )
        medium_keywords = (
            "excel",
            "xlsx",
            "spreadsheet",
            "csv",
            "table",
            "debug",
            "migration",
            "analysis",
            "report",
            "json",
        )

        if any(keyword in text for keyword in hard_keywords):
            return "gpt-5.4"
        if len(instruction) > 3000 or (skill and (skill.scripts or len(skill.content) > 2000)):
            return "gpt-5.4"
        if any(keyword in text for keyword in medium_keywords) or len(instruction) > 1400:
            return "gpt-5.3-codex"
        if len(instruction) > 700:
            return "gpt-5.2"
        return "gpt-5.1"
