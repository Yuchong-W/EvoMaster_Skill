"""Docker executor for skill evaluation."""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Optional
import docker

from ..core.types import TaskContext, SkillBundle


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
        self.skillsbench_root = Path(skillsbench_root)
        self.client = docker.from_env()

    def execute_skill(
        self,
        task_id: str,
        skill: SkillBundle,
        instruction: str,
        output_path: str = "/root/output.json",
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
        dockerfile_path = task_dir / "environment" / "Dockerfile"

        if not dockerfile_path.exists():
            return {
                "success": False,
                "output_file": "",
                "execution_log": "",
                "error": f"Dockerfile not found: {dockerfile_path}",
                "exit_code": -1,
            }

        # Get image name from Dockerfile or use default
        image_name = self._get_image_name(task_id)

        # Build container
        try:
            container = self.client.containers.run(
                image_name,
                detach=True,
                mem_limit="4g",
                cpu_period=100000,
                cpu_quota=200000,
            )
        except docker.errors.ImageNotFound:
            # Build from Dockerfile
            image_name = f"masterskill:{task_id}"
            self._build_image(str(dockerfile_path), image_name)
            container = self.client.containers.run(
                image_name,
                detach=True,
                mem_limit="4g",
                cpu_period=100000,
                cpu_quota=200000,
            )

        try:
            # Copy skill to container
            skill_path = f"/tmp/skill_{skill.skill_id}"
            skill_dir = Path(skill_path)
            skill_dir.mkdir(exist_ok=True)
            (skill_dir / "SKILL.md").write_text(skill.to_skill_md())

            # Copy skill scripts
            if skill.scripts:
                scripts_dir = skill_dir / "scripts"
                scripts_dir.mkdir(exist_ok=True)
                for name, content in skill.scripts.items():
                    (scripts_dir / name).write_text(content)

            # Copy skill into container
            tar_data = self._make_tar(skill_path)
            container.put_archive("/root/.skills", tar_data)

            # Write instruction
            container.put_archive("/root", self._make_tar_content(
                "instruction.md", instruction
            ))

            # Execute model with skill
            result = self._run_with_skill(
                container,
                skill,
                output_path,
                timeout,
            )

            # Get output file
            output_file = self._get_file(container, output_path)

            # Get execution log
            execution_log = result.decode("utf-8", errors="replace")

            return {
                "success": result.returncode == 0,
                "output_file": output_file,
                "execution_log": execution_log,
                "error": "" if result.returncode == 0 else "Execution failed",
                "exit_code": result.returncode,
            }

        finally:
            container.remove(force=True)

    def run_real_test(
        self,
        task_id: str,
        output_path: str = "/root/output.json",
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
        tests_dir = task_dir / "tests"
        test_file = tests_dir / "test_outputs.py"

        if not test_file.exists():
            return {"passed": False, "score": 0.0, "details": "Test file not found", "exit_code": -1}

        # Build/run container with test
        image_name = f"masterskill:{task_id}"

        try:
            self._build_image(str(task_dir / "environment" / "Dockerfile"), image_name)
        except docker.errors.BuildError:
            return {"passed": False, "score": 0.0, "details": "Docker build failed", "exit_code": -1}

        try:
            container = self.client.containers.run(
                image_name,
                detach=True,
                mem_limit="4g",
            )

            # Run test
            exec_result = container.exec_run(
                f"python -m pytest {test_file} -v",
                socket=True,
                stream=True,
                timeout=timeout,
            )

            output = b""
            for chunk in exec_result.output:
                output += chunk

            details = output.decode("utf-8", errors="replace")
            passed = "PASSED" in details or "passed" in details

            # Try to extract score
            score = 1.0 if passed else 0.0

            return {
                "passed": passed,
                "score": score,
                "details": details,
                "exit_code": 0,
            }

        finally:
            container.remove(force=True)

    def run_task(
        self,
        task_id: str,
        instruction: str,
        output_path: str = "/root/output.json",
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
        task_dir = self.skillsbench_root / "tasks" / task_id
        dockerfile_path = task_dir / "environment" / "Dockerfile"

        if not dockerfile_path.exists():
            return {
                "passed": False,
                "output": "",
                "execution_log": "",
                "error": f"Dockerfile not found: {dockerfile_path}",
                "exit_code": -1,
            }

        image_name = f"masterskill:{task_id}"

        try:
            self._build_image(str(dockerfile_path), image_name)
        except docker.errors.BuildError as e:
            return {
                "passed": False,
                "output": "",
                "execution_log": "",
                "error": f"Docker build failed: {e}",
                "exit_code": -1,
            }

        try:
            container = self.client.containers.run(
                image_name,
                detach=True,
                mem_limit="4g",
            )

            # Write instruction
            container.put_archive("/root", self._make_tar_content(
                "instruction.md", instruction
            ))

            # Run Claude Code CLI to attempt the task
            result = self._run_model_attempt(
                container,
                output_path=output_path,
                timeout=timeout,
            )

            output = b""
            for chunk in result.output:
                output += chunk

            execution_log = output.decode("utf-8", errors="replace")

            # Check if output file was created
            output_content = self._get_file(container, output_path)
            passed = output_content != "" and result.returncode == 0

            return {
                "passed": passed,
                "output": output_content,
                "execution_log": execution_log,
                "error": "" if passed else "Model could not solve autonomously",
                "exit_code": result.returncode,
            }

        finally:
            container.remove(force=True)

    def _get_image_name(self, task_id: str) -> str:
        """Get image name for a task."""
        return f"skillsbench:{task_id}"

    def _build_image(self, dockerfile_path: str, image_name: str) -> None:
        """Build Docker image from Dockerfile."""
        context_path = Path(dockerfile_path).parent
        self.client.images.build(
            path=str(context_path),
            tag=image_name,
            rm=True,
        )

    def _run_with_skill(
        self,
        container,
        skill: SkillBundle,
        output_path: str,
        timeout: int,
    ) -> subprocess.CompletedProcess:
        """Run Claude Code CLI with skill in container.

        Uses Claude Code CLI --print mode to execute the task:
        1. Read instruction.md
        2. Read SKILL.md if available
        3. Attempt to solve and write output to output_path
        4. Capture all terminal output
        """
        from ..agent_config import get_agent_params

        exec_cfg = get_agent_params("execution")
        model = exec_cfg.get("model", "claude-sonnet-4-6")
        cli_path = exec_cfg.get("cli_path", "claude")
        timeout_sec = exec_cfg.get("timeout", 600)

        # Build the prompt that tells Claude Code what to do
        skill_note = f"If there's a skill guide at /root/.skills/{skill.skill_id}/SKILL.md, read it and use it." if skill else ""

        prompt = f"""You are solving a task. Read the instruction and any available skill guide, then solve the task and write your output.

First, read the instruction:
```
$(cat /root/instruction.md)
```

{skill_note}

Your goal: Solve the task and write the final output to {output_path} as JSON.

Write your output and ensure the file is created at {output_path}.
"""

        # Escape single quotes in prompt for bash
        escaped_prompt = prompt.replace("'", "'\"'\"'")

        # Use Claude Code CLI with --print mode
        # --print: Run in non-interactive mode and print result
        # --model: Specify the model to use
        cmd = f"""
export ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY && \
{cli_path} --model {model} --print '{escaped_prompt}' 2>&1
"""

        result = container.exec_run(
            f"bash -c '{cmd}'",
            socket=True,
            stream=True,
            timeout=timeout_sec,
        )

        output = b""
        for chunk in result.output:
            output += chunk

        return subprocess.CompletedProcess(args=cmd, returncode=result.exit_code, stdout=output)

    def _run_model_attempt(
        self,
        container,
        output_path: str,
        timeout: int,
    ) -> subprocess.CompletedProcess:
        """Run Claude Code CLI without skill (initial model attempt).

        This is the baseline attempt to see if the model can solve the task
        without any external skill.
        """
        from ..agent_config import get_agent_params

        exec_cfg = get_agent_params("execution")
        model = exec_cfg.get("model", "claude-sonnet-4-6")
        cli_path = exec_cfg.get("cli_path", "claude")
        timeout_sec = exec_cfg.get("timeout", 600)

        prompt = f"""You are solving a task. Read the instruction, then solve the task and write your output.

Read the instruction:
```
$(cat /root/instruction.md)
```

Your goal: Solve the task and write the final output to {output_path} as JSON.

Write your output and ensure the file is created at {output_path}.
"""

        escaped_prompt = prompt.replace("'", "'\"'\"'")

        cmd = f"""
export ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY && \
{cli_path} --model {model} --print '{escaped_prompt}' 2>&1
"""

        result = container.exec_run(
            f"bash -c '{cmd}'",
            socket=True,
            stream=True,
            timeout=timeout_sec,
        )

        output = b""
        for chunk in result.output:
            output += chunk

        return subprocess.CompletedProcess(args=cmd, returncode=result.exit_code, stdout=output)

    def _make_tar(self, directory: str) -> bytes:
        """Create a tar archive of a directory."""
        import tarfile
        import io

        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
            tar.add(directory, arcname=os.path.basename(directory))
        return tar_buffer.getvalue()

    def _make_tar_content(self, filename: str, content: str) -> bytes:
        """Create a tar archive with a single file."""
        import tarfile
        import io

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
