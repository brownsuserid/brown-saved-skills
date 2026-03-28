import csv
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DataRecord:
    id: int
    name: str
    value: float
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class DataProcessor:
    def __init__(self, source_dir: Path):
        self.source_dir = source_dir
        self._records: list[DataRecord] = []
        self._errors: list[str] = []

    def load_csv(self, filename: str, delimiter: str = ",") -> int:
        filepath = self.source_dir / filename
        count = 0
        with open(filepath) as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                try:
                    record = DataRecord(
                        id=int(row["id"]),
                        name=row["name"],
                        value=float(row["value"]),
                        tags=row.get("tags", "").split(";") if row.get("tags") else [],
                    )
                    self._records.append(record)
                    count += 1
                except (KeyError, ValueError) as e:
                    self._errors.append(f"Row {count}: {e}")
        return count

    def load_json(self, filename: str) -> int:
        filepath = self.source_dir / filename
        with open(filepath) as f:
            data = json.load(f)
        count = 0
        for item in data:
            record = DataRecord(**item)
            self._records.append(record)
            count += 1
        return count

    def filter_by_value(self, min_val: float, max_val: float) -> list[DataRecord]:
        return [r for r in self._records if min_val <= r.value <= max_val]

    def filter_by_tags(self, tags: list[str], match_all: bool = False) -> list[DataRecord]:
        if match_all:
            return [r for r in self._records if all(t in r.tags for t in tags)]
        return [r for r in self._records if any(t in r.tags for t in tags)]

    def aggregate(self, group_by: str = "name") -> dict[str, dict]:
        groups: dict[str, list[float]] = {}
        for record in self._records:
            key = getattr(record, group_by, str(record.id))
            groups.setdefault(key, []).append(record.value)

        result = {}
        for key, values in groups.items():
            result[key] = {
                "count": len(values),
                "sum": sum(values),
                "mean": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
            }
        return result

    def export_json(self, output_path: Path) -> int:
        data = []
        for r in self._records:
            data.append(
                {
                    "id": r.id,
                    "name": r.name,
                    "value": r.value,
                    "tags": r.tags,
                    "metadata": r.metadata,
                }
            )
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        return len(data)

    @property
    def record_count(self) -> int:
        return len(self._records)

    @property
    def errors(self) -> list[str]:
        return self._errors.copy()
