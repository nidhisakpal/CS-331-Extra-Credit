"""Menu-driven B-tree project for CS 331.

The program stores student records in a B-tree using id as the primary key.
It supports loading records from a text file, insertion, deletion, search,
printing the tree shape, and printing records in sorted id order.
"""

from __future__ import annotations

import csv
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class StudentRecord:
    """A single row in the student table."""

    id: int
    studentname: str
    gpa: float

    def __str__(self) -> str:
        return f"{self.id:4d} | {self.studentname:<24} | {self.gpa:.2f}"


class BTreeNode:
    """One node in a B-tree.

    A B-tree node stores keys in sorted order. For this project, each key is a
    student id, and the matching value is the complete StudentRecord.
    """

    def __init__(self, leaf: bool = True) -> None:
        self.leaf = leaf
        self.keys: List[int] = []
        self.records: List[StudentRecord] = []
        self.children: List[BTreeNode] = []

    def __repr__(self) -> str:
        return f"BTreeNode(leaf={self.leaf}, keys={self.keys})"


class BTree:
    """B-tree implementation with configurable minimum degree t.

    For minimum degree t:
    - Every node except the root has at least t - 1 keys.
    - Every node can have at most 2t - 1 keys.
    - A non-leaf node with k keys has k + 1 children.
    """

    def __init__(self, t: int = 3) -> None:
        if t < 2:
            raise ValueError("Minimum degree t must be at least 2.")
        self.t = t
        self.root = BTreeNode(leaf=True)

    def search(self, key: int, node: Optional[BTreeNode] = None) -> Optional[StudentRecord]:
        """Search for a student id and return its record if found."""

        if node is None:
            node = self.root

        # Find the first key greater than or equal to the search key.
        i = 0
        while i < len(node.keys) and key > node.keys[i]:
            i += 1

        # If the key is present in this node, return the full record.
        if i < len(node.keys) and key == node.keys[i]:
            return node.records[i]

        # If this is a leaf, the key is not in the tree.
        if node.leaf:
            return None

        # Otherwise, continue searching the child where this key would belong.
        return self.search(key, node.children[i])

    def insert(self, record: StudentRecord) -> bool:
        """Insert a student record.

        Returns False if the id already exists, because id is the primary key.
        """

        if self.search(record.id) is not None:
            return False

        root = self.root
        if len(root.keys) == (2 * self.t) - 1:
            # The root is full. B-trees split full nodes before descending so
            # insertion never has to place a key into an overfull node.
            new_root = BTreeNode(leaf=False)
            new_root.children.append(root)
            self.root = new_root
            self._split_child(new_root, 0)
            self._insert_non_full(new_root, record)
        else:
            self._insert_non_full(root, record)
        return True

    def _insert_non_full(self, node: BTreeNode, record: StudentRecord) -> None:
        """Insert into a node that is guaranteed not to be full."""

        i = len(node.keys) - 1

        if node.leaf:
            # In a leaf, shift larger keys one position right and place the new
            # record where its id belongs so the keys stay sorted.
            node.keys.append(0)
            node.records.append(record)
            while i >= 0 and record.id < node.keys[i]:
                node.keys[i + 1] = node.keys[i]
                node.records[i + 1] = node.records[i]
                i -= 1
            node.keys[i + 1] = record.id
            node.records[i + 1] = record
            return

        # In an internal node, choose the child that should receive the key.
        while i >= 0 and record.id < node.keys[i]:
            i -= 1
        i += 1

        # If that child is full, split it first. The median key moves up into
        # this node, and then we choose which of the two children to descend to.
        if len(node.children[i].keys) == (2 * self.t) - 1:
            self._split_child(node, i)
            if record.id > node.keys[i]:
                i += 1

        self._insert_non_full(node.children[i], record)

    def _split_child(self, parent: BTreeNode, child_index: int) -> None:
        """Split a full child into two nodes and move its median key up.

        This is the key operation that keeps the B-tree balanced. A full child
        with 2t - 1 keys becomes two children with t - 1 keys each, while the
        middle key is promoted into the parent.
        """

        t = self.t
        full_child = parent.children[child_index]
        new_child = BTreeNode(leaf=full_child.leaf)

        median_key = full_child.keys[t - 1]
        median_record = full_child.records[t - 1]

        new_child.keys = full_child.keys[t:]
        new_child.records = full_child.records[t:]
        full_child.keys = full_child.keys[: t - 1]
        full_child.records = full_child.records[: t - 1]

        if not full_child.leaf:
            new_child.children = full_child.children[t:]
            full_child.children = full_child.children[:t]

        parent.keys.insert(child_index, median_key)
        parent.records.insert(child_index, median_record)
        parent.children.insert(child_index + 1, new_child)

    def delete(self, key: int) -> bool:
        """Delete a record by id. Returns True if a record was removed."""

        if self.search(key) is None:
            return False

        self._delete(self.root, key)

        # If the root lost its last key and has a child, shorten the tree.
        if len(self.root.keys) == 0 and not self.root.leaf:
            self.root = self.root.children[0]

        return True

    def _delete(self, node: BTreeNode, key: int) -> None:
        """Delete a key from the subtree rooted at node.

        The deletion algorithm keeps every node we descend into at or above the
        minimum key count when possible. That prevents underflow after deleting.
        """

        idx = self._find_key_index(node, key)

        if idx < len(node.keys) and node.keys[idx] == key:
            if node.leaf:
                self._remove_from_leaf(node, idx)
            else:
                self._remove_from_internal(node, idx)
            return

        if node.leaf:
            return

        child_index = idx
        if len(node.children[child_index].keys) < self.t:
            self._fill_child(node, child_index)
            if child_index > len(node.keys):
                child_index -= 1

        self._delete(node.children[child_index], key)

    def _find_key_index(self, node: BTreeNode, key: int) -> int:
        """Return the index of the first key greater than or equal to key."""

        idx = 0
        while idx < len(node.keys) and node.keys[idx] < key:
            idx += 1
        return idx

    def _remove_from_leaf(self, node: BTreeNode, idx: int) -> None:
        """Remove a key and record directly from a leaf node."""

        node.keys.pop(idx)
        node.records.pop(idx)

    def _remove_from_internal(self, node: BTreeNode, idx: int) -> None:
        """Remove a key from an internal node.

        Internal deletion replaces the key with either its predecessor or
        successor when a neighboring child has enough keys. If both children are
        minimal, they are merged and deletion continues in the merged child.
        """

        key = node.keys[idx]

        if len(node.children[idx].keys) >= self.t:
            pred_key, pred_record = self._get_predecessor(node.children[idx])
            node.keys[idx] = pred_key
            node.records[idx] = pred_record
            self._delete(node.children[idx], pred_key)
        elif len(node.children[idx + 1].keys) >= self.t:
            succ_key, succ_record = self._get_successor(node.children[idx + 1])
            node.keys[idx] = succ_key
            node.records[idx] = succ_record
            self._delete(node.children[idx + 1], succ_key)
        else:
            self._merge_children(node, idx)
            self._delete(node.children[idx], key)

    def _get_predecessor(self, node: BTreeNode) -> Tuple[int, StudentRecord]:
        """Return the largest key and record in a subtree."""

        current = node
        while not current.leaf:
            current = current.children[-1]
        return current.keys[-1], current.records[-1]

    def _get_successor(self, node: BTreeNode) -> Tuple[int, StudentRecord]:
        """Return the smallest key and record in a subtree."""

        current = node
        while not current.leaf:
            current = current.children[0]
        return current.keys[0], current.records[0]

    def _fill_child(self, parent: BTreeNode, child_index: int) -> None:
        """Give a child more keys by borrowing from siblings or by merging."""

        if child_index > 0 and len(parent.children[child_index - 1].keys) >= self.t:
            self._borrow_from_previous(parent, child_index)
        elif (
            child_index < len(parent.children) - 1
            and len(parent.children[child_index + 1].keys) >= self.t
        ):
            self._borrow_from_next(parent, child_index)
        else:
            if child_index < len(parent.children) - 1:
                self._merge_children(parent, child_index)
            else:
                self._merge_children(parent, child_index - 1)

    def _borrow_from_previous(self, parent: BTreeNode, child_index: int) -> None:
        """Move one key from the left sibling through the parent into a child."""

        child = parent.children[child_index]
        sibling = parent.children[child_index - 1]

        child.keys.insert(0, parent.keys[child_index - 1])
        child.records.insert(0, parent.records[child_index - 1])

        if not child.leaf:
            child.children.insert(0, sibling.children.pop())

        parent.keys[child_index - 1] = sibling.keys.pop()
        parent.records[child_index - 1] = sibling.records.pop()

    def _borrow_from_next(self, parent: BTreeNode, child_index: int) -> None:
        """Move one key from the right sibling through the parent into a child."""

        child = parent.children[child_index]
        sibling = parent.children[child_index + 1]

        child.keys.append(parent.keys[child_index])
        child.records.append(parent.records[child_index])

        if not child.leaf:
            child.children.append(sibling.children.pop(0))

        parent.keys[child_index] = sibling.keys.pop(0)
        parent.records[child_index] = sibling.records.pop(0)

    def _merge_children(self, parent: BTreeNode, child_index: int) -> None:
        """Merge a child, a parent separator key, and the next child."""

        child = parent.children[child_index]
        sibling = parent.children[child_index + 1]

        child.keys.append(parent.keys.pop(child_index))
        child.records.append(parent.records.pop(child_index))
        child.keys.extend(sibling.keys)
        child.records.extend(sibling.records)

        if not child.leaf:
            child.children.extend(sibling.children)

        parent.children.pop(child_index + 1)

    def traverse(self) -> List[StudentRecord]:
        """Return all records in sorted order by id."""

        records: List[StudentRecord] = []
        self._traverse_node(self.root, records)
        return records

    def _traverse_node(self, node: BTreeNode, records: List[StudentRecord]) -> None:
        """In-order traversal of the B-tree."""

        for i, record in enumerate(node.records):
            if not node.leaf:
                self._traverse_node(node.children[i], records)
            records.append(record)
        if not node.leaf:
            self._traverse_node(node.children[-1], records)

    def display(self) -> None:
        """Print the B-tree level by level."""

        self._display_node(self.root, level=0, child_label="root")

    def _display_node(self, node: BTreeNode, level: int, child_label: str) -> None:
        """Recursive helper for displaying the tree structure."""

        indent = "    " * level
        keys = ", ".join(str(key) for key in node.keys)
        print(f"{indent}{child_label}: [{keys}]")
        if not node.leaf:
            for i, child in enumerate(node.children):
                self._display_node(child, level + 1, f"child {i}")


def parse_student_line(line: str) -> Optional[StudentRecord]:
    """Parse one row from comma, tab, or whitespace separated text."""

    line = line.strip()
    if not line:
        return None

    if line.lower().replace(" ", "") in {"id,studentname,gpa", "id\tstudentname\tgpa"}:
        return None

    if "," in line:
        parts = next(csv.reader([line]))
    elif "\t" in line:
        parts = line.split("\t")
    else:
        parts = re.split(r"\s+", line)

    parts = [part.strip() for part in parts if part.strip()]
    if len(parts) < 3:
        raise ValueError(f"Could not parse row: {line}")

    student_id = int(parts[0])
    gpa = float(parts[-1])
    name = " ".join(parts[1:-1])
    return StudentRecord(student_id, name, gpa)


def load_records_from_file(filename: str) -> List[StudentRecord]:
    """Load student records from a text file."""

    path = Path(filename)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filename}")

    records: List[StudentRecord] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            try:
                record = parse_student_line(line)
            except ValueError as exc:
                raise ValueError(f"Line {line_number}: {exc}") from exc
            if record is not None:
                records.append(record)
    return records


def print_records(records: List[StudentRecord]) -> None:
    """Print records in a simple table."""

    if not records:
        print("No records to display.")
        return

    print("  ID | Student Name             | GPA")
    print("-" * 39)
    for record in records:
        print(record)


def generate_random_student(existing_ids: set[int]) -> StudentRecord:
    """Generate one random student with an unused id."""

    first_names = [
        "Avery",
        "Blake",
        "Casey",
        "Drew",
        "Emerson",
        "Finley",
        "Harper",
        "Jordan",
        "Morgan",
        "Quinn",
        "Reese",
        "Skyler",
        "Taylor",
        "Riley",
        "Parker",
    ]
    last_names = [
        "Adams",
        "Bennett",
        "Carter",
        "Diaz",
        "Ellis",
        "Foster",
        "Garcia",
        "Hayes",
        "Ibrahim",
        "Johnson",
        "Kim",
        "Lopez",
        "Nguyen",
        "Patel",
        "Young",
    ]

    new_id = random.randint(101, 999)
    while new_id in existing_ids:
        new_id = random.randint(101, 999)

    name = f"{random.choice(first_names)} {random.choice(last_names)}"
    gpa = round(random.uniform(2.00, 4.00), 2)
    return StudentRecord(new_id, name, gpa)


def insert_random_students(tree: BTree, count: int = 5) -> List[StudentRecord]:
    """Insert random students and return the records that were added."""

    existing_ids = {record.id for record in tree.traverse()}
    added: List[StudentRecord] = []
    for _ in range(count):
        record = generate_random_student(existing_ids)
        tree.insert(record)
        existing_ids.add(record.id)
        added.append(record)
    return added


def delete_random_students(tree: BTree, count: int = 20) -> List[int]:
    """Delete up to count random students from the tree."""

    records = tree.traverse()
    if not records:
        return []

    ids = [record.id for record in records]
    ids_to_delete = random.sample(ids, min(count, len(ids)))
    for student_id in ids_to_delete:
        tree.delete(student_id)
    return ids_to_delete


def prompt_int(message: str) -> Optional[int]:
    """Read an integer from the user. Return None if invalid."""

    try:
        return int(input(message).strip())
    except ValueError:
        print("Please enter a valid integer.")
        return None


def prompt_float(message: str) -> Optional[float]:
    """Read a float from the user. Return None if invalid."""

    try:
        return float(input(message).strip())
    except ValueError:
        print("Please enter a valid number.")
        return None


def load_into_tree(tree: BTree, filename: str) -> int:
    """Load records from a file into an existing B-tree."""

    records = load_records_from_file(filename)
    inserted = 0
    for record in records:
        if tree.insert(record):
            inserted += 1
    return inserted


def menu() -> None:
    """Run the interactive menu."""

    print("CS 331 B-tree Student Index")
    degree = prompt_int("Enter minimum degree t for the B-tree (default 3): ")
    if degree is None:
        degree = 3

    try:
        tree = BTree(t=degree)
    except ValueError as exc:
        print(exc)
        print("Using default t = 3.")
        tree = BTree(t=3)

    while True:
        print("\nMenu")
        print("1. Load data from file")
        print("2. Display B-tree")
        print("3. Insert a student")
        print("4. Insert 5 random students")
        print("5. Delete a student by id")
        print("6. Delete 20 random students")
        print("7. Search by id")
        print("8. Print all records in sorted order")
        print("9. Exit")

        choice = input("Choose an option: ").strip()

        if choice == "1":
            filename = input("Enter filename (default students.txt): ").strip() or "students.txt"
            try:
                inserted = load_into_tree(tree, filename)
                print(f"Loaded {inserted} new records into the B-tree.")
            except (FileNotFoundError, ValueError) as exc:
                print(f"Error: {exc}")

        elif choice == "2":
            print("\nB-tree structure:")
            tree.display()

        elif choice == "3":
            student_id = prompt_int("Student id: ")
            if student_id is None:
                continue
            name = input("Student name: ").strip()
            gpa = prompt_float("GPA: ")
            if gpa is None:
                continue
            if tree.insert(StudentRecord(student_id, name, gpa)):
                print("Student inserted.")
            else:
                print("That id already exists. Insert canceled.")

        elif choice == "4":
            added = insert_random_students(tree, 5)
            print("Inserted these random students:")
            print_records(added)

        elif choice == "5":
            student_id = prompt_int("Student id to delete: ")
            if student_id is None:
                continue
            if tree.delete(student_id):
                print("Student deleted.")
            else:
                print("Student id not found.")

        elif choice == "6":
            deleted_ids = delete_random_students(tree, 20)
            if deleted_ids:
                print(f"Deleted ids: {', '.join(str(item) for item in deleted_ids)}")
            else:
                print("No records available to delete.")

        elif choice == "7":
            student_id = prompt_int("Student id to search for: ")
            if student_id is None:
                continue
            record = tree.search(student_id)
            if record:
                print("Found:")
                print_records([record])
            else:
                print("Student id not found.")

        elif choice == "8":
            print_records(tree.traverse())

        elif choice == "9":
            print("Goodbye.")
            break

        else:
            print("Invalid option. Please choose 1 through 9.")


if __name__ == "__main__":
    menu()
