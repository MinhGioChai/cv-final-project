"""Official Pet test-list subset; explicit eight-class map, never a 37-way claim."""
import re

from .candidates import candidate, ensure_unique


def read_pet_list(payload: bytes):
    rows = []
    for line in payload.decode("utf-8-sig").splitlines():
        if not line.strip() or line.startswith("#"):continue
        parts = line.split()
        if len(parts) != 4:raise ValueError("Expected image/class/species/breed columns")
        name, class_id, species, breed_id = parts
        match = re.fullmatch(r"([A-Za-z_]+)_([1-9][0-9]*)", name)
        if not match or not all(x.isdigit() for x in parts[1:]):raise ValueError("Invalid Pet annotation")
        item = dict(image=name, class_id=int(class_id), species=int(species), breed_id=int(breed_id), breed=match.group(1))
        if (not 1 <= item["class_id"] <= 37 or item["species"] not in {1, 2}
                or not 1 <= item["breed_id"] <= 25):raise ValueError("Unknown Pet label")
        rows.append(item)
    if not rows or len({r["image"] for r in rows}) != len(rows):raise ValueError("Empty/duplicate Pet images")
    return rows


def parse_oxford_pet(payload: bytes, *, revision: str, breeds: list[str]):
    if len(breeds) != 8 or len(set(breeds)) != 8:raise ValueError("Choose exactly eight distinct breeds before scoring")
    records = read_pet_list(payload)
    mapping = {name: label for name, label in zip(breeds, "ABCDEFGH")}
    if not set(breeds).issubset({r["breed"] for r in records}):raise ValueError("Selected breed missing from source test list")
    labels = {}
    rows = []
    for record in records:
        if record["breed"] not in mapping:continue
        if record["species"] != 2:raise ValueError("This proposal selects eight dog breeds; species must be Dog=2")
        source_label = (record["class_id"], record["breed_id"], record["species"])
        if labels.setdefault(record["breed"], source_label) != source_label:raise ValueError("Inconsistent Pet class mapping")
        rows.append(candidate(dataset="oxford_pet", split="test", revision=revision,
            row_id=record["image"], record=record, namespace="oxford_iiit_pet", image_id=record["image"],
            image_ref=record["image"] + ".jpg", task="fine_grained", category=record["breed"],
            question="Which dog breed is shown?", truth=mapping[record["breed"]],
            metadata={"source_class_id": record["class_id"], "source_species": record["species"],
                      "source_breed_id": record["breed_id"], "breed": record["breed"],
                      "candidate_map": mapping, "evaluation_scope": "proposed_eight_way_dog_subset_not_37_way"}))
    return ensure_unique(rows)
