"""Meta memory: cross-task meta-knowledge and methods."""

import json
from pathlib import Path
from typing import Optional
from dataclasses import asdict

from ..core.types import MetaMemory, ProblemType, EffectiveMethod, IneffectiveMethod


class MetaMemoryStore:
    """Deep memory layer: cross-task meta-knowledge.

    Stores:
    - Effective methods (transferable across tasks)
    - Ineffective methods (with failure reasons)
    - Success factors
    - Domain/problem-type mappings
    """

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.meta_file = self.data_dir / "meta_memory.json"
        self._ensure_file()

    def _ensure_file(self) -> None:
        if not self.meta_file.exists():
            self._save({})

    def _load(self) -> dict[str, dict]:
        return json.loads(self.meta_file.read_text())

    def _save(self, data: dict[str, dict]) -> None:
        self.meta_file.write_text(json.dumps(data, indent=2))

    def _make_key(self, problem_type: ProblemType, domain: str, modeling: str) -> str:
        """Create a unique key for a problem profile."""
        return f"{problem_type.value}::{domain}::{modeling}"

    def get(self, problem_type: ProblemType, domain: str, modeling: str) -> Optional[MetaMemory]:
        """Get meta memory for a specific problem profile."""
        data = self._load()
        key = self._make_key(problem_type, domain, modeling)
        if key not in data:
            return None
        return MetaMemory(**data[key])

    def get_by_tags(self, problem_type: ProblemType, domain: str, modeling: str) -> list[MetaMemory]:
        """Get all meta memories with matching tags (for reuse试探)."""
        data = self._load()
        results = []
        for key, val in data.items():
            mm = MetaMemory(**val)
            if (mm.problem_type == problem_type and
                mm.domain == domain and
                mm.problem_modeling == modeling):
                results.append(mm)
        return results

    def add(self, meta: MetaMemory) -> None:
        """Add or update meta memory."""
        data = self._load()
        key = self._make_key(meta.problem_type, meta.domain, meta.problem_modeling)
        data[key] = asdict(meta)
        self._save(data)

    def add_effective_method(self, problem_type: ProblemType, domain: str, modeling: str,
                            method: EffectiveMethod) -> None:
        """Add an effective method to meta memory."""
        data = self._load()
        key = self._make_key(problem_type, domain, modeling)

        if key not in data:
            meta = MetaMemory(
                problem_type=problem_type,
                domain=domain,
                problem_modeling=modeling,
            )
            meta.effective_methods.append(method)
            data[key] = asdict(meta)
        else:
            meta = MetaMemory(**data[key])
            # Avoid duplicates
            existing_ids = [m.method_id for m in meta.effective_methods]
            if method.method_id not in existing_ids:
                meta.effective_methods.append(method)
            data[key] = asdict(meta)

        self._save(data)

    def add_ineffective_method(self, problem_type: ProblemType, domain: str, modeling: str,
                              method: IneffectiveMethod) -> None:
        """Add an ineffective method to meta memory."""
        data = self._load()
        key = self._make_key(problem_type, domain, modeling)

        if key not in data:
            meta = MetaMemory(
                problem_type=problem_type,
                domain=domain,
                problem_modeling=modeling,
            )
            meta.ineffective_methods.append(method)
            data[key] = asdict(meta)
        else:
            meta = MetaMemory(**data[key])
            # Avoid duplicates
            existing_ids = [m.method_id for m in meta.ineffective_methods]
            if method.method_id not in existing_ids:
                meta.ineffective_methods.append(method)
            data[key] = asdict(meta)

        self._save(data)

    def add_success_factor(self, problem_type: ProblemType, domain: str, modeling: str,
                          factor: str) -> None:
        """Add a success factor to meta memory."""
        data = self._load()
        key = self._make_key(problem_type, domain, modeling)

        if key not in data:
            meta = MetaMemory(
                problem_type=problem_type,
                domain=domain,
                problem_modeling=modeling,
            )
            meta.success_factors.append(factor)
            data[key] = asdict(meta)
        else:
            meta = MetaMemory(**data[key])
            if factor not in meta.success_factors:
                meta.success_factors.append(factor)
            data[key] = asdict(meta)

        self._save(data)

    def is_method_ineffective(self, method_id: str) -> bool:
        """Check if a method is known to be ineffective."""
        data = self._load()
        for val in data.values():
            meta = MetaMemory(**val)
            for method in meta.ineffective_methods:
                if method.method_id == method_id:
                    return True
        return False

    def get_transferable_skills(self, problem_type: ProblemType, domain: str, modeling: str,
                                min_transferability: str = "medium") -> list[EffectiveMethod]:
        """Get transferable skills for a problem profile."""
        meta_list = self.get_by_tags(problem_type, domain, modeling)
        transferability_order = {"high": 0, "medium": 1, "low": 2}
        min_level = transferability_order.get(min_transferability, 1)

        results = []
        for meta in meta_list:
            for method in meta.effective_methods:
                if transferability_order.get(method.transferability, 2) <= min_level:
                    results.append(method)

        return results
