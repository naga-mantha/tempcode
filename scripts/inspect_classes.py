import ast
import os
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional

ROOT = Path(__file__).resolve().parents[1]
APPS_DIR = ROOT / "apps"


def is_python_file(p: Path) -> bool:
    return p.suffix == ".py" and "__pycache__" not in p.parts


def module_name_from_path(path: Path) -> str:
    rel = path.relative_to(ROOT)
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1][:-3]  # strip .py
    return ".".join(parts)


def dotted_name(node: ast.AST) -> Optional[str]:
    # Convert an AST for a base into a dotted string if possible
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parts: List[str] = []
        cur: Optional[ast.AST] = node
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
            return ".".join(reversed(parts))
        return None
    if isinstance(node, ast.Subscript):  # e.g., Generic[Foo]
        return dotted_name(node.value)
    if isinstance(node, ast.Call):  # e.g., Base()
        return dotted_name(node.func)
    return None


def collect_classes() -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    classes: Dict[str, List[str]] = {}
    class_to_module: Dict[str, str] = {}

    for path in APPS_DIR.rglob("*.py"):
        if not is_python_file(path):
            continue
        try:
            src = path.read_text(encoding="utf-8")
        except Exception:
            continue
        try:
            tree = ast.parse(src, filename=str(path))
        except Exception:
            continue

        mod = module_name_from_path(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                name = node.name
                fqn = f"{mod}.{name}"
                bases: List[str] = []
                for b in node.bases:
                    dn = dotted_name(b)
                    if dn is None:
                        try:
                            dn = ast.unparse(b)  # type: ignore[attr-defined]
                        except Exception:
                            dn = "<expr>"
                    bases.append(dn)
                classes[fqn] = bases
                class_to_module[fqn] = mod

    return classes, class_to_module


def build_resolution_maps(classes: Dict[str, List[str]]):
    # Map simple names and FQNs to FQNs for resolution
    name_to_fqns: Dict[str, Set[str]] = {}
    for fqn in classes.keys():
        simple = fqn.split(".")[-1]
        name_to_fqns.setdefault(simple, set()).add(fqn)
        name_to_fqns.setdefault(fqn, set()).add(fqn)
    return name_to_fqns


def resolve_base_to_fqn(base: str, name_to_fqns: Dict[str, Set[str]]) -> Optional[str]:
    # Try exact match first
    if base in name_to_fqns and len(name_to_fqns[base]) == 1:
        return next(iter(name_to_fqns[base]))
    # Try tail of dotted name
    tail = base.split(".")[-1]
    if tail in name_to_fqns and len(name_to_fqns[tail]) == 1:
        return next(iter(name_to_fqns[tail]))
    return None


def build_graph(classes: Dict[str, List[str]]):
    name_to_fqns = build_resolution_maps(classes)
    children: Dict[str, Set[str]] = {fqn: set() for fqn in classes}
    parents: Dict[str, Set[str]] = {fqn: set() for fqn in classes}
    external_parents: Dict[str, List[str]] = {fqn: [] for fqn in classes}

    for child, bases in classes.items():
        for base in bases:
            resolved = resolve_base_to_fqn(base, name_to_fqns)
            if resolved:
                children[resolved].add(child)
                parents[child].add(resolved)
            else:
                external_parents[child].append(base)

    return children, parents, external_parents


def find_roots(classes: Dict[str, List[str]], parents: Dict[str, Set[str]]):
    return sorted([c for c in classes if not parents[c]])


def print_tree(classes: Dict[str, List[str]]):
    children, parents, external_parents = build_graph(classes)
    roots = find_roots(classes, parents)

    def label(fqn: str) -> str:
        mod, name = fqn.rsplit(".", 1)
        bases = classes.get(fqn, [])
        # Only show external bases on the node label for context
        ext = [b for b in external_parents[fqn] if b]
        suffix = f" (bases: {', '.join(ext)})" if ext else ""
        return f"{name} [{mod}]{suffix}"

    def walk(node: str, prefix: str = ""):
        print(prefix + label(node))
        kids = sorted(children.get(node, []))
        for i, ch in enumerate(kids):
            last = i == len(kids) - 1
            branch = "`- " if last else "|- "
            next_prefix = prefix + ("   " if last else "|  ")
            print(prefix + branch, end="")
            walk(ch, next_prefix)

    if not classes:
        print("No classes found under apps/.")
        return

    printed: Set[str] = set()
    for r in roots:
        walk(r)
        printed.add(r)
        print()

    # Any disconnected or cyclic leftovers
    remaining = sorted(set(classes.keys()) - printed)
    if remaining:
        print("(Unplaced classes)")
        for fqn in remaining:
            print("-", label(fqn))


def main():
    if not APPS_DIR.exists():
        print("apps/ directory not found from:", ROOT)
        return
    classes, _ = collect_classes()
    print_tree(classes)


if __name__ == "__main__":
    main()
