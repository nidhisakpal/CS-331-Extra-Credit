"""Menu-driven B+ tree project for CS 331.

This version uses a B+ tree, not a regular B-tree.

Important B+ tree idea:
- Internal nodes store only separator keys used for navigation.
- Full student records are stored only in the leaf nodes.
- Leaf nodes are linked together so sorted traversal can scan the leaves from
  left to right, similar to how database indexes support range scans.
"""

# This import lets type hints refer to classes before Python has finished
# defining them. That is useful because BPlusTreeNode stores child nodes of its
# own class.
from __future__ import annotations

# bisect_left finds where a key belongs inside a sorted list.
# bisect_right chooses the child pointer in an internal B+ tree node.
from bisect import bisect_left, bisect_right

# csv correctly parses comma-separated rows, including quoted names if the input
# file ever contains them.
import csv

# random is used for the menu options that insert or delete random students.
import random

# re gives us regular expressions for flexible whitespace-separated parsing.
import re

# dataclass creates a clean class for one student table row.
from dataclasses import dataclass

# Path is a clear, cross-platform way to work with files.
from pathlib import Path

# These typing imports make function inputs and outputs easier to understand.
from typing import List, Optional, Tuple


@dataclass
class StudentRecord:
    """A single row in the student table.

    In database language, this is the full table record. The B+ tree uses
    ``id`` as the search key, but the leaf node stores this complete object.
    """

    # id is the primary key. Each student id should appear only once.
    id: int

    # studentname stores the student's full name.
    studentname: str

    # gpa stores the student's grade point average.
    gpa: float

    def __str__(self) -> str:
        """Return one formatted output row for printing tables."""

        # The spacing keeps the columns aligned when records are printed.
        return f"{self.id:4d} | {self.studentname:<24} | {self.gpa:.2f}"


class BPlusTreeNode:
    """One node in a B+ tree.

    A leaf node stores real records. An internal node stores separator keys and
    child pointers only. This is the main difference between this B+ tree and
    the earlier B-tree version.
    """

    def __init__(self, leaf: bool = True) -> None:
        # leaf tells us whether this node is a bottom-level data node.
        self.leaf = leaf

        # In a leaf, keys are student ids for actual records.
        # In an internal node, keys are separator values used to choose children.
        self.keys: List[int] = []

        # records is used only for leaf nodes. records[i] belongs to keys[i].
        self.records: List[StudentRecord] = []

        # children is used only for internal nodes. If an internal node has k
        # keys, it should have k + 1 children.
        self.children: List[BPlusTreeNode] = []

        # next links one leaf to the next leaf. This makes sorted traversal fast
        # because we can scan the leaf chain without revisiting internal nodes.
        self.next: Optional[BPlusTreeNode] = None

    def __repr__(self) -> str:
        """Return a debug-friendly representation of the node."""

        # This helps if a node is printed while debugging.
        return f"BPlusTreeNode(leaf={self.leaf}, keys={self.keys})"


class BPlusTree:
    """B+ tree implementation with configurable minimum degree t.

    This project uses a simple degree rule similar to the original assignment:
    - A node can store at most 2t - 1 keys.
    - A non-root node should store at least t - 1 keys.
    - Internal-node keys are separators derived from child subtrees.
    - All full records live in the leaf level.
    """

    def __init__(self, t: int = 3) -> None:
        # t must be at least 2 so every split creates valid left/right nodes.
        if t < 2:
            raise ValueError("Minimum degree t must be at least 2.")

        # Save the minimum degree selected by the user.
        self.t = t

        # max_keys is the largest number of keys allowed in one node.
        self.max_keys = (2 * t) - 1

        # min_keys is the smallest number of keys allowed in a non-root node.
        self.min_keys = t - 1

        # A new B+ tree starts as one empty leaf root.
        self.root = BPlusTreeNode(leaf=True)

    def search(self, key: int) -> Optional[StudentRecord]:
        """Search for a student id and return the matching record if found."""

        # First follow separator keys down to the leaf where this key belongs.
        leaf, _ = self._find_leaf(key)

        # The leaf keys are sorted, so bisect_left gives the only possible
        # position where the key could be stored.
        index = bisect_left(leaf.keys, key)

        # If the position is valid and the id matches, return the full record.
        if index < len(leaf.keys) and leaf.keys[index] == key:
            return leaf.records[index]

        # If the key is not in the leaf, it is not in the B+ tree.
        return None

    def insert(self, record: StudentRecord) -> bool:
        """Insert one student record into the B+ tree.

        Returns False if the id already exists, because id is the primary key.
        """

        # Reject duplicate primary keys before changing the tree.
        if self.search(record.id) is not None:
            return False

        # Find the leaf where this record belongs, plus the path of parents.
        leaf, path = self._find_leaf(record.id)

        # Insert the id into the leaf's sorted key list.
        insert_index = bisect_left(leaf.keys, record.id)
        leaf.keys.insert(insert_index, record.id)

        # Insert the full record at the matching position.
        leaf.records.insert(insert_index, record)

        # If the leaf overflowed, split it and add a separator to the parent.
        if len(leaf.keys) > self.max_keys:
            self._split_leaf(leaf, path)
        else:
            # If the smallest key in this leaf changed, parent separators may
            # need to be refreshed.
            self._refresh_path(path)

        # Return True so the menu can report success.
        return True

    def delete(self, key: int) -> bool:
        """Delete a student by id. Returns True if a record was removed."""

        # Find the leaf where this id should be stored.
        leaf, path = self._find_leaf(key)

        # Locate the id inside the leaf.
        index = bisect_left(leaf.keys, key)

        # If the id is not present, no deletion occurs.
        if index >= len(leaf.keys) or leaf.keys[index] != key:
            return False

        # Remove both the key and the full record from the leaf.
        leaf.keys.pop(index)
        leaf.records.pop(index)

        # If the root is also a leaf, it is allowed to become empty.
        if leaf is self.root:
            return True

        # If the leaf still has enough keys, only separators may need updating.
        if len(leaf.keys) >= self.min_keys:
            self._refresh_path(path)
        else:
            # Otherwise, fix the underflow by borrowing or merging.
            self._rebalance_after_delete(leaf, path)

        # A record was successfully removed.
        return True

    def traverse(self) -> List[StudentRecord]:
        """Return all records in sorted order by id."""

        # Start at the leftmost leaf, which contains the smallest ids.
        current = self._leftmost_leaf()

        # Store records as we scan the linked leaf list.
        records: List[StudentRecord] = []

        # Follow leaf.next pointers until there are no more leaves.
        while current is not None:
            records.extend(current.records)
            current = current.next

        # The leaf chain is sorted, so this list is sorted by id.
        return records

    def display(self) -> None:
        """Print the B+ tree structure level by level."""

        # Begin recursive printing at the root.
        self._display_node(self.root, level=0, child_label="root")

        # Also show the leaf chain because linked leaves are a key B+ tree idea.
        print("leaf chain:", self._leaf_chain_string())

    def _find_leaf(self, key: int) -> Tuple[BPlusTreeNode, List[Tuple[BPlusTreeNode, int]]]:
        """Find the leaf where key belongs and return the path to it.

        The path is a list of (parent, child_index) pairs. It is used after
        insertions and deletions so parent nodes can be updated or rebalanced.
        """

        # Start every search at the root.
        current = self.root

        # Store the route taken from the root down to the target leaf.
        path: List[Tuple[BPlusTreeNode, int]] = []

        # Continue until a leaf node is reached.
        while not current.leaf:
            # Internal keys are separator keys. bisect_right chooses the child
            # whose range should contain the target key.
            child_index = bisect_right(current.keys, key)

            # Remember this parent and the child position selected.
            path.append((current, child_index))

            # Descend to the selected child.
            current = current.children[child_index]

        # current is now the leaf where the key exists or should be inserted.
        return current, path

    def _split_leaf(self, leaf: BPlusTreeNode, path: List[Tuple[BPlusTreeNode, int]]) -> None:
        """Split an overfull leaf node into two linked leaves."""

        # The leaf has max_keys + 1 records. Split it roughly in half.
        split_index = len(leaf.keys) // 2

        # Create a new right leaf.
        new_leaf = BPlusTreeNode(leaf=True)

        # Move the right half of keys and records into the new leaf.
        new_leaf.keys = leaf.keys[split_index:]
        new_leaf.records = leaf.records[split_index:]

        # Keep the left half in the original leaf.
        leaf.keys = leaf.keys[:split_index]
        leaf.records = leaf.records[:split_index]

        # Link the new leaf into the leaf chain immediately after the old leaf.
        new_leaf.next = leaf.next
        leaf.next = new_leaf

        # The new leaf's first key becomes the separator in the parent.
        self._insert_child_in_parent(leaf, new_leaf, path)

    def _insert_child_in_parent(
        self,
        left_child: BPlusTreeNode,
        right_child: BPlusTreeNode,
        path: List[Tuple[BPlusTreeNode, int]],
    ) -> None:
        """Insert a newly split right child into the parent node."""

        # If there is no parent, the split happened at the root.
        if not path:
            # Create a new internal root with the two split nodes as children.
            new_root = BPlusTreeNode(leaf=False)
            new_root.children = [left_child, right_child]

            # Separator keys are always derived from child subtrees.
            self._refresh_keys(new_root)

            # Replace the old root with the new root.
            self.root = new_root
            return

        # Get the parent and the index where left_child is stored.
        parent, child_index = path.pop()

        # Insert the new right child immediately after the left child.
        parent.children.insert(child_index + 1, right_child)

        # Recompute separator keys after changing the child list.
        self._refresh_keys(parent)

        # If the parent overflowed, split it too.
        if len(parent.keys) > self.max_keys:
            self._split_internal(parent, path)
        else:
            # Otherwise, refresh any ancestors whose separator keys changed.
            self._refresh_path(path)

    def _split_internal(
        self,
        internal: BPlusTreeNode,
        path: List[Tuple[BPlusTreeNode, int]],
    ) -> None:
        """Split an overfull internal node.

        Unlike leaf nodes, internal nodes do not contain records. They contain
        child pointers and separator keys. After splitting the child pointer
        list, each internal node recomputes its separator keys from its children.
        """

        # Split based on children rather than keys because internal keys are
        # derived from children. If there are 7 children, this gives 3 and 4.
        split_index = len(internal.children) // 2

        # Create the new right internal node.
        new_internal = BPlusTreeNode(leaf=False)

        # Move the right half of the child pointers into the new node.
        new_internal.children = internal.children[split_index:]

        # Keep the left half in the original node.
        internal.children = internal.children[:split_index]

        # Recompute separator keys for both internal nodes.
        self._refresh_keys(internal)
        self._refresh_keys(new_internal)

        # Insert the new right internal node into the parent.
        self._insert_child_in_parent(internal, new_internal, path)

    def _rebalance_after_delete(
        self,
        node: BPlusTreeNode,
        path: List[Tuple[BPlusTreeNode, int]],
    ) -> None:
        """Fix a node that has too few keys after deletion.

        The algorithm first tries to borrow from a sibling. If neither sibling
        has an extra key, it merges nodes. This is the B+ tree deletion logic
        that keeps the tree balanced after records are removed.
        """

        # Continue upward while the current node is not the root and is too small.
        while node is not self.root and len(node.keys) < self.min_keys:
            # The path tells us the parent and where node sits among siblings.
            parent, child_index = path.pop()

            # Identify neighboring siblings if they exist.
            left_sibling = parent.children[child_index - 1] if child_index > 0 else None
            right_sibling = (
                parent.children[child_index + 1]
                if child_index + 1 < len(parent.children)
                else None
            )

            # Try borrowing from the left sibling first.
            if left_sibling is not None and len(left_sibling.keys) > self.min_keys:
                self._borrow_from_left(node, left_sibling)
                self._refresh_keys(parent)
                self._refresh_path(path)
                return

            # If the left sibling cannot lend, try the right sibling.
            if right_sibling is not None and len(right_sibling.keys) > self.min_keys:
                self._borrow_from_right(node, right_sibling)
                self._refresh_keys(parent)
                self._refresh_path(path)
                return

            # If borrowing is impossible, merge with a sibling.
            if left_sibling is not None:
                self._merge_nodes(left_sibling, node)
                parent.children.pop(child_index)
                node = parent
            elif right_sibling is not None:
                self._merge_nodes(node, right_sibling)
                parent.children.pop(child_index + 1)
                node = parent

            # Recompute parent separators after removing a child.
            self._refresh_keys(parent)

            # If the root has only one child, collapse the height of the tree.
            if parent is self.root and not parent.leaf and len(parent.children) == 1:
                self.root = parent.children[0]
                return

        # If the loop ended because node now has enough keys, refresh ancestors.
        self._refresh_path(path)

    def _borrow_from_left(self, node: BPlusTreeNode, sibling: BPlusTreeNode) -> None:
        """Borrow one entry or child pointer from the left sibling."""

        if node.leaf:
            # For leaves, move the left sibling's largest record to the front
            # of the underfull node.
            node.keys.insert(0, sibling.keys.pop())
            node.records.insert(0, sibling.records.pop())
        else:
            # For internal nodes, move the sibling's rightmost child pointer.
            node.children.insert(0, sibling.children.pop())

            # Separator keys are derived from child pointers, so refresh both.
            self._refresh_keys(sibling)
            self._refresh_keys(node)

    def _borrow_from_right(self, node: BPlusTreeNode, sibling: BPlusTreeNode) -> None:
        """Borrow one entry or child pointer from the right sibling."""

        if node.leaf:
            # For leaves, move the right sibling's smallest record to the end
            # of the underfull node.
            node.keys.append(sibling.keys.pop(0))
            node.records.append(sibling.records.pop(0))
        else:
            # For internal nodes, move the sibling's leftmost child pointer.
            node.children.append(sibling.children.pop(0))

            # Separator keys are derived from child pointers, so refresh both.
            self._refresh_keys(sibling)
            self._refresh_keys(node)

    def _merge_nodes(self, left: BPlusTreeNode, right: BPlusTreeNode) -> None:
        """Merge right node into left node."""

        if left.leaf:
            # Leaf merge moves all records from right into left.
            left.keys.extend(right.keys)
            left.records.extend(right.records)

            # Preserve the linked leaf chain by skipping over the removed node.
            left.next = right.next
        else:
            # Internal merge moves all child pointers into the left node.
            left.children.extend(right.children)

            # Recompute separators after changing children.
            self._refresh_keys(left)

    def _refresh_keys(self, internal: BPlusTreeNode) -> None:
        """Recompute separator keys for one internal node."""

        # Leaf nodes do not have separator keys to recompute.
        if internal.leaf:
            return

        # In this B+ tree, key i stores the smallest key in child i + 1.
        internal.keys = [self._first_key(child) for child in internal.children[1:]]

    def _refresh_path(self, path: List[Tuple[BPlusTreeNode, int]]) -> None:
        """Refresh separator keys along a saved root-to-leaf path."""

        # Refresh from the bottom upward because parent separators depend on
        # child subtrees.
        for parent, _ in reversed(path):
            self._refresh_keys(parent)

    def _first_key(self, node: BPlusTreeNode) -> int:
        """Return the smallest key stored anywhere in a subtree."""

        # Follow the leftmost child until we reach a leaf.
        current = node
        while not current.leaf:
            current = current.children[0]

        # The first key in the leftmost leaf is the subtree's smallest key.
        return current.keys[0]

    def _leftmost_leaf(self) -> BPlusTreeNode:
        """Return the leftmost leaf in the B+ tree."""

        # Start at the root.
        current = self.root

        # Keep following child 0 until the leaf level is reached.
        while not current.leaf:
            current = current.children[0]

        # This leaf contains the smallest records in the index.
        return current

    def _display_node(self, node: BPlusTreeNode, level: int, child_label: str) -> None:
        """Recursive helper for printing the B+ tree structure."""

        # Indentation makes child levels visually nest under parent levels.
        indent = "    " * level

        # Label leaves differently so it is clear where actual records live.
        node_type = "leaf" if node.leaf else "internal"

        # Show the keys stored in this node.
        keys = ", ".join(str(key) for key in node.keys)
        print(f"{indent}{child_label} ({node_type}): [{keys}]")

        # Internal nodes recursively print their children.
        if not node.leaf:
            for i, child in enumerate(node.children):
                self._display_node(child, level + 1, f"child {i}")

    def _leaf_chain_string(self) -> str:
        """Return a printable version of the linked leaf chain."""

        # Start with the smallest leaf.
        current = self._leftmost_leaf()

        # Store each leaf's key list as text.
        parts: List[str] = []

        # Follow the linked leaves from left to right.
        while current is not None:
            parts.append("[" + ", ".join(str(key) for key in current.keys) + "]")
            current = current.next

        # Use arrows to show the links between leaves.
        return " -> ".join(parts)


def parse_student_line(line: str) -> Optional[StudentRecord]:
    """Parse one row from comma, tab, or whitespace separated text."""

    # Remove leading/trailing spaces and the newline at the end of the row.
    line = line.strip()

    # Ignore blank lines.
    if not line:
        return None

    # Skip the standard CSV header.
    if line.lower().replace(" ", "") in {"id,studentname,gpa", "id\tstudentname\tgpa"}:
        return None

    # Use CSV parsing if the row contains commas.
    if "," in line:
        parts = next(csv.reader([line]))

    # Use tab splitting if the row contains tabs.
    elif "\t" in line:
        parts = line.split("\t")

    # Otherwise, split on one or more spaces.
    else:
        parts = re.split(r"\s+", line)

    # Strip whitespace around each field and remove empty fields.
    parts = [part.strip() for part in parts if part.strip()]

    # A valid row needs at least id, name, and gpa.
    if len(parts) < 3:
        raise ValueError(f"Could not parse row: {line}")

    # Column 1 is the primary key.
    student_id = int(parts[0])

    # The last column is GPA.
    gpa = float(parts[-1])

    # Everything between id and GPA is the student name.
    name = " ".join(parts[1:-1])

    # Return the row as a StudentRecord object.
    return StudentRecord(student_id, name, gpa)


def load_records_from_file(filename: str) -> List[StudentRecord]:
    """Load student records from a text file."""

    # Convert the input string to a Path object.
    path = Path(filename)

    # Give a clear error if the file cannot be found.
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filename}")

    # Accumulate parsed records in this list.
    records: List[StudentRecord] = []

    # Open the file as UTF-8 text.
    with path.open("r", encoding="utf-8") as file:
        # Track line numbers so parse errors are easy to locate.
        for line_number, line in enumerate(file, start=1):
            try:
                record = parse_student_line(line)
            except ValueError as exc:
                # Add line number context to parsing errors.
                raise ValueError(f"Line {line_number}: {exc}") from exc

            # None means the line was blank or a header.
            if record is not None:
                records.append(record)

    # Return all loaded student rows.
    return records


def print_records(records: List[StudentRecord]) -> None:
    """Print records in a simple table."""

    # Avoid printing an empty table.
    if not records:
        print("No records to display.")
        return

    # Print the table header.
    print("  ID | Student Name             | GPA")
    print("-" * 39)

    # Print one formatted line per student.
    for record in records:
        print(record)


def generate_random_student(existing_ids: set[int]) -> StudentRecord:
    """Generate one random student with an unused id."""

    # First names for random records.
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

    # Last names for random records.
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

    # Pick an id above the sample file's original 1-100 range.
    new_id = random.randint(101, 999)

    # Keep trying until the id is unique.
    while new_id in existing_ids:
        new_id = random.randint(101, 999)

    # Build a random full name.
    name = f"{random.choice(first_names)} {random.choice(last_names)}"

    # Generate a GPA between 2.00 and 4.00.
    gpa = round(random.uniform(2.00, 4.00), 2)

    # Return the complete new record.
    return StudentRecord(new_id, name, gpa)


def insert_random_students(tree: BPlusTree, count: int = 5) -> List[StudentRecord]:
    """Insert random students and return the records that were added."""

    # Gather existing primary keys so new random records do not duplicate them.
    existing_ids = {record.id for record in tree.traverse()}

    # Keep track of inserted records for display.
    added: List[StudentRecord] = []

    # Generate and insert the requested number of records.
    for _ in range(count):
        record = generate_random_student(existing_ids)
        tree.insert(record)
        existing_ids.add(record.id)
        added.append(record)

    # Return the records that were added.
    return added


def delete_random_students(tree: BPlusTree, count: int = 20) -> List[int]:
    """Delete up to count random students from the tree."""

    # Get all current records from the B+ tree leaves.
    records = tree.traverse()

    # If the tree is empty, there is nothing to delete.
    if not records:
        return []

    # Deletion is by primary key, so extract ids.
    ids = [record.id for record in records]

    # Choose unique ids to delete. min() handles trees with fewer than count rows.
    ids_to_delete = random.sample(ids, min(count, len(ids)))

    # Delete each selected id.
    for student_id in ids_to_delete:
        tree.delete(student_id)

    # Return deleted ids so the menu can show what happened.
    return ids_to_delete


def prompt_int(message: str) -> Optional[int]:
    """Read an integer from the user. Return None if invalid."""

    try:
        # input() returns text, strip() removes spaces, and int() converts it.
        return int(input(message).strip())
    except ValueError:
        # Invalid input should not crash the CLI.
        print("Please enter a valid integer.")
        return None


def prompt_float(message: str) -> Optional[float]:
    """Read a float from the user. Return None if invalid."""

    try:
        # Convert the user's text into a floating-point value.
        return float(input(message).strip())
    except ValueError:
        # Invalid input should not crash the CLI.
        print("Please enter a valid number.")
        return None


def load_into_tree(tree: BPlusTree, filename: str) -> int:
    """Load records from a file into an existing B+ tree."""

    # Parse the input file into StudentRecord objects.
    records = load_records_from_file(filename)

    # Count only records that were inserted. Duplicate ids are skipped.
    inserted = 0

    # Insert each record using the B+ tree index.
    for record in records:
        if tree.insert(record):
            inserted += 1

    # Return how many new records were added.
    return inserted


def menu() -> None:
    """Run the interactive menu."""

    # Print a title for the program.
    print("CS 331 B+ Tree Student Index")

    # Ask for the minimum degree t.
    degree = prompt_int("Enter minimum degree t for the B+ tree (default 3): ")

    # Use 3 if the user entered invalid text.
    if degree is None:
        degree = 3

    try:
        # Create the B+ tree using the requested degree.
        tree = BPlusTree(t=degree)
    except ValueError as exc:
        # Recover from invalid degree values such as 0 or 1.
        print(exc)
        print("Using default t = 3.")
        tree = BPlusTree(t=3)

    # Keep showing the menu until the user exits.
    while True:
        # Print all required project operations.
        print("\nMenu")
        print("1. Load data from file")
        print("2. Display B+ tree")
        print("3. Insert a student")
        print("4. Insert 5 random students")
        print("5. Delete a student by id")
        print("6. Delete 20 random students")
        print("7. Search by id")
        print("8. Print all records in sorted order")
        print("9. Exit")

        # Read the user's menu choice.
        choice = input("Choose an option: ").strip()

        if choice == "1":
            # Load a file. Pressing Enter uses the sample file.
            filename = input("Enter filename (default students.txt): ").strip() or "students.txt"
            try:
                inserted = load_into_tree(tree, filename)
                print(f"Loaded {inserted} new records into the B+ tree.")
            except (FileNotFoundError, ValueError) as exc:
                # Show file/parsing errors without crashing.
                print(f"Error: {exc}")

        elif choice == "2":
            # Display internal separator nodes, leaves, and the leaf chain.
            print("\nB+ tree structure:")
            tree.display()

        elif choice == "3":
            # Insert one user-provided student.
            student_id = prompt_int("Student id: ")
            if student_id is None:
                continue

            # Read the student name.
            name = input("Student name: ").strip()

            # Read the GPA.
            gpa = prompt_float("GPA: ")
            if gpa is None:
                continue

            # Insert the record. Duplicate primary keys are rejected.
            if tree.insert(StudentRecord(student_id, name, gpa)):
                print("Student inserted.")
            else:
                print("That id already exists. Insert canceled.")

        elif choice == "4":
            # Insert five randomly generated students.
            added = insert_random_students(tree, 5)
            print("Inserted these random students:")
            print_records(added)

        elif choice == "5":
            # Delete one student by primary key.
            student_id = prompt_int("Student id to delete: ")
            if student_id is None:
                continue

            # Run B+ tree deletion.
            if tree.delete(student_id):
                print("Student deleted.")
            else:
                print("Student id not found.")

        elif choice == "6":
            # Delete twenty random students, or fewer if fewer records exist.
            deleted_ids = delete_random_students(tree, 20)
            if deleted_ids:
                print(f"Deleted ids: {', '.join(str(item) for item in deleted_ids)}")
            else:
                print("No records available to delete.")

        elif choice == "7":
            # Search for one student by primary key.
            student_id = prompt_int("Student id to search for: ")
            if student_id is None:
                continue

            # B+ tree search always descends to a leaf.
            record = tree.search(student_id)
            if record:
                print("Found:")
                print_records([record])
            else:
                print("Student id not found.")

        elif choice == "8":
            # Sorted output scans the linked leaf level from left to right.
            print_records(tree.traverse())

        elif choice == "9":
            # Exit the menu loop.
            print("Goodbye.")
            break

        else:
            # Handle choices outside 1 through 9.
            print("Invalid option. Please choose 1 through 9.")


if __name__ == "__main__":
    # Run the menu only when this file is executed directly.
    menu()
