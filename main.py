"""Menu-driven B-tree project for CS 331.

The program stores student records in a B-tree using id as the primary key.
It supports loading records from a text file, insertion, deletion, search,
printing the tree shape, and printing records in sorted id order.
"""

# This import lets type hints refer to classes before Python has finished
# defining them. That is useful below because BTreeNode stores child BTreeNodes.
from __future__ import annotations

# csv helps correctly parse comma-separated files, including names that might
# be quoted in a real input file.
import csv

# random is used only for the extra-credit style operations that insert/delete
# randomly generated students.
import random

# re gives us regular expressions, which make whitespace-separated parsing
# flexible when the input file is not comma-separated or tab-separated.
import re

# dataclass automatically creates a simple initializer for StudentRecord.
from dataclasses import dataclass

# Path gives a clean, cross-platform way to check and open files.
from pathlib import Path

# These typing imports make function inputs and return values clearer.
from typing import List, Optional, Tuple


@dataclass
class StudentRecord:
    """A single row in the student table.

    This is the "record" that the B-tree stores as a value. The B-tree key is
    only the id, but the value attached to that key is the whole StudentRecord.
    """

    # id acts like a database primary key. Each id should be unique.
    id: int

    # studentname stores the student's full name from the input table.
    studentname: str

    # gpa stores the student's numeric grade point average.
    gpa: float

    def __str__(self) -> str:
        """Return a nicely formatted table row for printing."""

        # The formatting pads the id and name columns so output lines up.
        return f"{self.id:4d} | {self.studentname:<24} | {self.gpa:.2f}"


class BTreeNode:
    """One node in a B-tree.

    A B-tree node stores keys in sorted order. For this project, each key is a
    student id, and the matching value is the complete StudentRecord.
    """

    def __init__(self, leaf: bool = True) -> None:
        # leaf tells us whether this node has children. A leaf node is at the
        # bottom of the tree and contains no child pointers.
        self.leaf = leaf

        # keys contains sorted student ids. These are the values used for
        # searching, inserting, deleting, and splitting.
        self.keys: List[int] = []

        # records[i] is the full StudentRecord that belongs to keys[i].
        # Keeping these lists parallel is what maps each key to a full row.
        self.records: List[StudentRecord] = []

        # children contains child nodes. For an internal node with k keys, there
        # should be k + 1 children. Leaf nodes keep this list empty.
        self.children: List[BTreeNode] = []

    def __repr__(self) -> str:
        """Return a debug-friendly version of the node."""

        # This is helpful if a node is printed in the Python console.
        return f"BTreeNode(leaf={self.leaf}, keys={self.keys})"


class BTree:
    """B-tree implementation with configurable minimum degree t.

    For minimum degree t:
    - Every node except the root has at least t - 1 keys.
    - Every node can have at most 2t - 1 keys.
    - A non-leaf node with k keys has k + 1 children.
    """

    def __init__(self, t: int = 3) -> None:
        # The minimum degree must be at least 2. If t were 1, the B-tree rules
        # would break because nodes could have too few keys to split/merge well.
        if t < 2:
            raise ValueError("Minimum degree t must be at least 2.")

        # Save the minimum degree so every operation knows the allowed node size.
        self.t = t

        # The tree starts with one empty leaf node, which is also the root.
        self.root = BTreeNode(leaf=True)

    def search(self, key: int, node: Optional[BTreeNode] = None) -> Optional[StudentRecord]:
        """Search for a student id and return its record if found.

        The search works like a database index lookup:
        1. Look inside the current node for the key.
        2. If it is not here and this is not a leaf, choose the correct child.
        3. Repeat until the key is found or a leaf proves it is missing.
        """

        # When the caller does not provide a node, begin at the root. Recursive
        # calls pass a child node here.
        if node is None:
            node = self.root

        # Find the first key greater than or equal to the search key.
        # Because node.keys is sorted, all keys before index i are too small.
        i = 0
        while i < len(node.keys) and key > node.keys[i]:
            i += 1

        # If the key is present in this node, return the full record.
        # The record is stored at the same index as the key.
        if i < len(node.keys) and key == node.keys[i]:
            return node.records[i]

        # If this is a leaf, the key is not in the tree.
        # There are no children left to search.
        if node.leaf:
            return None

        # Otherwise, continue searching the child where this key would belong.
        # Child i contains values between keys[i - 1] and keys[i].
        return self.search(key, node.children[i])

    def insert(self, record: StudentRecord) -> bool:
        """Insert a student record.

        Returns False if the id already exists, because id is the primary key.
        """

        # A primary key cannot appear twice, so search first to reject duplicate
        # ids before modifying the tree.
        if self.search(record.id) is not None:
            return False

        # Keep a short variable for readability because the root is used often.
        root = self.root

        # A node is full when it already has the maximum allowed number of keys.
        # For minimum degree t, the maximum is 2t - 1.
        if len(root.keys) == (2 * self.t) - 1:
            # The root is full. B-trees split full nodes before descending so
            # insertion never has to place a key into an overfull node.
            new_root = BTreeNode(leaf=False)

            # The old root becomes child 0 of the new root.
            new_root.children.append(root)

            # Replace the tree root before splitting so the promoted median key
            # has a parent to move into.
            self.root = new_root

            # Split old root. One median key moves into new_root.
            self._split_child(new_root, 0)

            # Now that the root has room, insert the record normally.
            self._insert_non_full(new_root, record)
        else:
            # If the root is not full, we can insert directly into the normal
            # recursive helper.
            self._insert_non_full(root, record)

        # Returning True tells the CLI that the insert succeeded.
        return True

    def _insert_non_full(self, node: BTreeNode, record: StudentRecord) -> None:
        """Insert into a node that is guaranteed not to be full.

        This helper is the standard B-tree insertion routine. Its important
        assumption is that the current node has space for one more key.
        """

        # Start at the rightmost key. We may move left while looking for the
        # correct sorted position for the new id.
        i = len(node.keys) - 1

        if node.leaf:
            # In a leaf, shift larger keys one position right and place the new
            # record where its id belongs so the keys stay sorted.

            # Add temporary space at the end of both parallel lists.
            node.keys.append(0)
            node.records.append(record)

            # Move every larger key/record one slot to the right.
            while i >= 0 and record.id < node.keys[i]:
                node.keys[i + 1] = node.keys[i]
                node.records[i + 1] = node.records[i]
                i -= 1

            # Insert the new key and matching record into the open slot.
            node.keys[i + 1] = record.id
            node.records[i + 1] = record
            return

        # In an internal node, choose the child that should receive the key.
        # Move left until we find the first key smaller than the new id.
        while i >= 0 and record.id < node.keys[i]:
            i -= 1

        # The child to descend into is one position to the right of that key.
        i += 1

        # If that child is full, split it first. The median key moves up into
        # this node, and then we choose which of the two children to descend to.
        if len(node.children[i].keys) == (2 * self.t) - 1:
            self._split_child(node, i)

            # After the split, node.keys[i] is the promoted median. If the new
            # id is larger than that median, it belongs in the new right child.
            if record.id > node.keys[i]:
                i += 1

        # Continue recursively until we reach a leaf.
        self._insert_non_full(node.children[i], record)

    def _split_child(self, parent: BTreeNode, child_index: int) -> None:
        """Split a full child into two nodes and move its median key up.

        This is the key operation that keeps the B-tree balanced. A full child
        with 2t - 1 keys becomes two children with t - 1 keys each, while the
        middle key is promoted into the parent.
        """

        # Use a local variable because t is used many times in this method.
        t = self.t

        # The parent owns the child that is too full.
        full_child = parent.children[child_index]

        # The new child will become the right half of the split node. It has
        # the same leaf/internal status as the original child.
        new_child = BTreeNode(leaf=full_child.leaf)

        # The median key is the key at index t - 1. It moves upward into the
        # parent and separates the left and right halves.
        median_key = full_child.keys[t - 1]
        median_record = full_child.records[t - 1]

        # Keys after the median move into the new right child.
        new_child.keys = full_child.keys[t:]
        new_child.records = full_child.records[t:]

        # Keys before the median remain in the original left child.
        full_child.keys = full_child.keys[: t - 1]
        full_child.records = full_child.records[: t - 1]

        # If the full child was internal, its children must also be split.
        # The first t children stay on the left; the remaining children move
        # to the new right child.
        if not full_child.leaf:
            new_child.children = full_child.children[t:]
            full_child.children = full_child.children[:t]

        # Insert the median key/record into the parent at the position where
        # the old child used to sit.
        parent.keys.insert(child_index, median_key)
        parent.records.insert(child_index, median_record)

        # The new right child goes immediately after the original child.
        parent.children.insert(child_index + 1, new_child)

    def delete(self, key: int) -> bool:
        """Delete a record by id. Returns True if a record was removed."""

        # Search first so the public method can clearly report whether anything
        # was actually deleted.
        if self.search(key) is None:
            return False

        # Run the recursive B-tree deletion algorithm starting at the root.
        self._delete(self.root, key)

        # If the root lost its last key and has a child, shorten the tree.
        # This can happen after merges near the top of the tree.
        if len(self.root.keys) == 0 and not self.root.leaf:
            self.root = self.root.children[0]

        # The key existed and was removed.
        return True

    def _delete(self, node: BTreeNode, key: int) -> None:
        """Delete a key from the subtree rooted at node.

        The deletion algorithm keeps every node we descend into at or above the
        minimum key count when possible. That prevents underflow after deleting.
        """

        # idx is the first position where key could appear in this node.
        idx = self._find_key_index(node, key)

        # Case 1: the key is stored in this node.
        if idx < len(node.keys) and node.keys[idx] == key:
            if node.leaf:
                # If the node is a leaf, deletion is simple: remove the key
                # and its matching record from the parallel lists.
                self._remove_from_leaf(node, idx)
            else:
                # If the node is internal, we cannot simply remove the key
                # because it separates two child subtrees. Use the standard
                # predecessor/successor/merge logic instead.
                self._remove_from_internal(node, idx)
            return

        # Case 2: the key is not in this node. If this is a leaf, the key is
        # not in the tree, so there is nothing else to do.
        if node.leaf:
            return

        # The key must be in child idx if it exists anywhere below this node.
        child_index = idx

        # Before descending into a child, make sure it has at least t keys.
        # This prevents it from dropping below the minimum after deletion.
        if len(node.children[child_index].keys) < self.t:
            self._fill_child(node, child_index)

            # Filling may merge the child with a sibling, which can reduce the
            # number of keys in the parent. If the chosen child moved left,
            # adjust the child index.
            if child_index > len(node.keys):
                child_index -= 1

        # Continue deletion in the corrected child.
        self._delete(node.children[child_index], key)

    def _find_key_index(self, node: BTreeNode, key: int) -> int:
        """Return the index of the first key greater than or equal to key."""

        # Start at the leftmost key.
        idx = 0

        # Move right while keys are still smaller than the target key.
        while idx < len(node.keys) and node.keys[idx] < key:
            idx += 1

        # This index is either where the key exists or where it would be.
        return idx

    def _remove_from_leaf(self, node: BTreeNode, idx: int) -> None:
        """Remove a key and record directly from a leaf node."""

        # Remove the id from the key list.
        node.keys.pop(idx)

        # Remove the matching full record from the same index.
        node.records.pop(idx)

    def _remove_from_internal(self, node: BTreeNode, idx: int) -> None:
        """Remove a key from an internal node.

        Internal deletion replaces the key with either its predecessor or
        successor when a neighboring child has enough keys. If both children are
        minimal, they are merged and deletion continues in the merged child.
        """

        # Save the key we are trying to remove. If both children merge, this
        # key will move down into the merged child and then be deleted there.
        key = node.keys[idx]

        # If the left child has enough keys, replace the current key with its
        # predecessor: the largest key smaller than it.
        if len(node.children[idx].keys) >= self.t:
            pred_key, pred_record = self._get_predecessor(node.children[idx])
            node.keys[idx] = pred_key
            node.records[idx] = pred_record

            # The predecessor record has been copied up, so delete its old copy
            # from the left subtree.
            self._delete(node.children[idx], pred_key)

        # Otherwise, if the right child has enough keys, replace the current key
        # with its successor: the smallest key larger than it.
        elif len(node.children[idx + 1].keys) >= self.t:
            succ_key, succ_record = self._get_successor(node.children[idx + 1])
            node.keys[idx] = succ_key
            node.records[idx] = succ_record

            # Delete the successor from its old location in the right subtree.
            self._delete(node.children[idx + 1], succ_key)

        # If both children have only the minimum number of keys, merge them with
        # the key from the parent, then delete from that merged node.
        else:
            self._merge_children(node, idx)
            self._delete(node.children[idx], key)

    def _get_predecessor(self, node: BTreeNode) -> Tuple[int, StudentRecord]:
        """Return the largest key and record in a subtree."""

        # The predecessor is found by going as far right as possible.
        current = node
        while not current.leaf:
            current = current.children[-1]

        # The largest key in the final leaf is the predecessor.
        return current.keys[-1], current.records[-1]

    def _get_successor(self, node: BTreeNode) -> Tuple[int, StudentRecord]:
        """Return the smallest key and record in a subtree."""

        # The successor is found by going as far left as possible.
        current = node
        while not current.leaf:
            current = current.children[0]

        # The smallest key in the final leaf is the successor.
        return current.keys[0], current.records[0]

    def _fill_child(self, parent: BTreeNode, child_index: int) -> None:
        """Give a child more keys by borrowing from siblings or by merging.

        This helper is used during deletion. Before deleting from a child, we
        want that child to have at least t keys if possible. If it has only
        t - 1 keys, deleting one more could violate the B-tree rules.
        """

        # First try borrowing from the left sibling. Borrowing is cheaper than
        # merging because it does not reduce the number of children.
        if child_index > 0 and len(parent.children[child_index - 1].keys) >= self.t:
            self._borrow_from_previous(parent, child_index)

        # If the left sibling cannot lend a key, try the right sibling.
        elif (
            child_index < len(parent.children) - 1
            and len(parent.children[child_index + 1].keys) >= self.t
        ):
            self._borrow_from_next(parent, child_index)

        # If neither sibling has extra keys, merge the child with one sibling.
        else:
            if child_index < len(parent.children) - 1:
                # Prefer merging with the right sibling when it exists.
                self._merge_children(parent, child_index)
            else:
                # If there is no right sibling, merge with the left sibling.
                self._merge_children(parent, child_index - 1)

    def _borrow_from_previous(self, parent: BTreeNode, child_index: int) -> None:
        """Move one key from the left sibling through the parent into a child."""

        # child is the node that needs one more key.
        child = parent.children[child_index]

        # sibling is the child immediately to the left.
        sibling = parent.children[child_index - 1]

        # Move the separating parent key down into the front of child.
        child.keys.insert(0, parent.keys[child_index - 1])
        child.records.insert(0, parent.records[child_index - 1])

        # If these are internal nodes, the sibling's rightmost child pointer
        # must also move so child keeps the correct number of children.
        if not child.leaf:
            child.children.insert(0, sibling.children.pop())

        # Move the left sibling's largest key up into the parent. This replaces
        # the separator key that was moved down.
        parent.keys[child_index - 1] = sibling.keys.pop()
        parent.records[child_index - 1] = sibling.records.pop()

    def _borrow_from_next(self, parent: BTreeNode, child_index: int) -> None:
        """Move one key from the right sibling through the parent into a child."""

        # child is the node that needs one more key.
        child = parent.children[child_index]

        # sibling is the child immediately to the right.
        sibling = parent.children[child_index + 1]

        # Move the separating parent key down to the end of child.
        child.keys.append(parent.keys[child_index])
        child.records.append(parent.records[child_index])

        # If these are internal nodes, the sibling's leftmost child pointer
        # follows the borrowed separator so child remains structurally valid.
        if not child.leaf:
            child.children.append(sibling.children.pop(0))

        # Move the right sibling's smallest key up into the parent.
        parent.keys[child_index] = sibling.keys.pop(0)
        parent.records[child_index] = sibling.records.pop(0)

    def _merge_children(self, parent: BTreeNode, child_index: int) -> None:
        """Merge a child, a parent separator key, and the next child.

        After merging, parent.children[child_index] contains:
        left child keys + separator key from parent + right sibling keys.
        """

        # The left child is where all merged keys will end up.
        child = parent.children[child_index]

        # The right sibling will be absorbed and then removed from parent.
        sibling = parent.children[child_index + 1]

        # Pull the separator key down from the parent into the left child.
        child.keys.append(parent.keys.pop(child_index))
        child.records.append(parent.records.pop(child_index))

        # Append all keys/records from the right sibling.
        child.keys.extend(sibling.keys)
        child.records.extend(sibling.records)

        # Internal nodes also need their children moved over.
        if not child.leaf:
            child.children.extend(sibling.children)

        # Remove the now-empty sibling pointer from the parent.
        parent.children.pop(child_index + 1)

    def traverse(self) -> List[StudentRecord]:
        """Return all records in sorted order by id."""

        # Accumulate records in this list as the recursive traversal visits
        # them in sorted key order.
        records: List[StudentRecord] = []

        # Start traversal from the root.
        self._traverse_node(self.root, records)

        # Return the complete sorted list to the caller.
        return records

    def _traverse_node(self, node: BTreeNode, records: List[StudentRecord]) -> None:
        """In-order traversal of the B-tree.

        For each key i in a node, the records in child i come before key i.
        The final child contains keys larger than the last key in the node.
        """

        # Visit each key/record in order.
        for i, record in enumerate(node.records):
            if not node.leaf:
                # Visit the child containing keys smaller than this record.
                self._traverse_node(node.children[i], records)

            # Add this node's record after its left child has been visited.
            records.append(record)

        # After the last key, visit the rightmost child if this is internal.
        if not node.leaf:
            self._traverse_node(node.children[-1], records)

    def display(self) -> None:
        """Print the B-tree level by level."""

        # Start recursive display at the root and label it clearly.
        self._display_node(self.root, level=0, child_label="root")

    def _display_node(self, node: BTreeNode, level: int, child_label: str) -> None:
        """Recursive helper for displaying the tree structure."""

        # Indentation makes deeper levels appear visually below their parents.
        indent = "    " * level

        # Show only ids in the tree diagram to keep the structure readable.
        keys = ", ".join(str(key) for key in node.keys)

        # Print this node's label and its sorted key list.
        print(f"{indent}{child_label}: [{keys}]")

        # Recursively display children underneath the current node.
        if not node.leaf:
            for i, child in enumerate(node.children):
                self._display_node(child, level + 1, f"child {i}")


def parse_student_line(line: str) -> Optional[StudentRecord]:
    """Parse one row from comma, tab, or whitespace separated text.

    The professor's file should be comma-separated, but this function accepts a
    few common formats so the project is more forgiving.
    """

    # Remove leading/trailing spaces and newline characters.
    line = line.strip()

    # Ignore blank lines instead of treating them as errors.
    if not line:
        return None

    # Skip a header row such as "id,studentname,gpa".
    if line.lower().replace(" ", "") in {"id,studentname,gpa", "id\tstudentname\tgpa"}:
        return None

    # Prefer CSV parsing when commas exist because names could be quoted.
    if "," in line:
        parts = next(csv.reader([line]))

    # If the row uses tabs, split on tabs.
    elif "\t" in line:
        parts = line.split("\t")

    # Otherwise, split on one or more whitespace characters.
    else:
        parts = re.split(r"\s+", line)

    # Clean up each parsed column and drop accidental empty columns.
    parts = [part.strip() for part in parts if part.strip()]

    # A valid row must have at least id, name, and gpa.
    if len(parts) < 3:
        raise ValueError(f"Could not parse row: {line}")

    # The first column is the primary key.
    student_id = int(parts[0])

    # The last column is GPA.
    gpa = float(parts[-1])

    # Everything between id and gpa is treated as the student's name. This
    # allows whitespace-separated names like "Emma Johnson".
    name = " ".join(parts[1:-1])

    # Create and return the StudentRecord object used by the B-tree.
    return StudentRecord(student_id, name, gpa)


def load_records_from_file(filename: str) -> List[StudentRecord]:
    """Load student records from a text file."""

    # Convert the filename string into a Path object.
    path = Path(filename)

    # Give a clear error if the file does not exist.
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filename}")

    # Store every parsed StudentRecord here.
    records: List[StudentRecord] = []

    # Open with UTF-8 so normal text files are read consistently.
    with path.open("r", encoding="utf-8") as file:
        # Keep line numbers so parse errors can identify the bad row.
        for line_number, line in enumerate(file, start=1):
            try:
                record = parse_student_line(line)
            except ValueError as exc:
                # Add line number context while preserving the original error.
                raise ValueError(f"Line {line_number}: {exc}") from exc

            # parse_student_line returns None for blank lines or headers.
            if record is not None:
                records.append(record)

    # Return all successfully parsed records.
    return records


def print_records(records: List[StudentRecord]) -> None:
    """Print records in a simple table."""

    # Avoid printing just the table header when there are no records.
    if not records:
        print("No records to display.")
        return

    # Print a small table header.
    print("  ID | Student Name             | GPA")
    print("-" * 39)

    # Each StudentRecord controls its own row formatting through __str__.
    for record in records:
        print(record)


def generate_random_student(existing_ids: set[int]) -> StudentRecord:
    """Generate one random student with an unused id."""

    # First names used to build realistic random student names.
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

    # Last names used to build realistic random student names.
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

    # Choose a random id above the original 1-100 sample range.
    new_id = random.randint(101, 999)

    # Keep trying until the id is not already in the tree.
    while new_id in existing_ids:
        new_id = random.randint(101, 999)

    # Randomly combine one first name and one last name.
    name = f"{random.choice(first_names)} {random.choice(last_names)}"

    # Pick a realistic GPA and round it to two decimal places.
    gpa = round(random.uniform(2.00, 4.00), 2)

    # Return a complete student record ready for insertion.
    return StudentRecord(new_id, name, gpa)


def insert_random_students(tree: BTree, count: int = 5) -> List[StudentRecord]:
    """Insert random students and return the records that were added."""

    # Build a set of ids that already exist so random generation avoids
    # primary-key duplicates.
    existing_ids = {record.id for record in tree.traverse()}

    # Track the records inserted so the CLI can display them.
    added: List[StudentRecord] = []

    # Generate and insert count new records.
    for _ in range(count):
        record = generate_random_student(existing_ids)
        tree.insert(record)

        # Update existing_ids immediately so two generated records in the same
        # batch cannot accidentally share an id.
        existing_ids.add(record.id)
        added.append(record)

    # Return the newly inserted records.
    return added


def delete_random_students(tree: BTree, count: int = 20) -> List[int]:
    """Delete up to count random students from the tree."""

    # Get all current records so we know which ids can be deleted.
    records = tree.traverse()

    # If the tree is empty, there is nothing to delete.
    if not records:
        return []

    # Extract only the ids because delete works by primary key.
    ids = [record.id for record in records]

    # Choose up to count unique ids. min() avoids errors if fewer than count
    # records are currently stored.
    ids_to_delete = random.sample(ids, min(count, len(ids)))

    # Delete each chosen id from the B-tree.
    for student_id in ids_to_delete:
        tree.delete(student_id)

    # Return deleted ids so the CLI can report exactly what happened.
    return ids_to_delete


def prompt_int(message: str) -> Optional[int]:
    """Read an integer from the user. Return None if invalid."""

    try:
        # input() reads text, strip() removes extra spaces, and int() converts
        # the result into an integer.
        return int(input(message).strip())
    except ValueError:
        # Invalid numeric input should not crash the program.
        print("Please enter a valid integer.")
        return None


def prompt_float(message: str) -> Optional[float]:
    """Read a float from the user. Return None if invalid."""

    try:
        # Convert the user's text input into a floating-point number.
        return float(input(message).strip())
    except ValueError:
        # Invalid GPA input should not crash the program.
        print("Please enter a valid number.")
        return None


def load_into_tree(tree: BTree, filename: str) -> int:
    """Load records from a file into an existing B-tree."""

    # Parse the file into StudentRecord objects first.
    records = load_records_from_file(filename)

    # Count only records that were actually inserted. Duplicate ids are skipped.
    inserted = 0

    # Insert each record using the B-tree insert method.
    for record in records:
        if tree.insert(record):
            inserted += 1

    # Return the number of new records added to the tree.
    return inserted


def menu() -> None:
    """Run the interactive menu.

    The menu is intentionally simple so a user can test every required database
    operation without needing to write any Python code.
    """

    # Print a title when the program starts.
    print("CS 331 B-tree Student Index")

    # Ask the user for the B-tree minimum degree. The assignment asks for a
    # configurable t value, so this lets the user choose it at runtime.
    degree = prompt_int("Enter minimum degree t for the B-tree (default 3): ")

    # If the user enters invalid text, use the default degree.
    if degree is None:
        degree = 3

    try:
        # Create the B-tree using the requested minimum degree.
        tree = BTree(t=degree)
    except ValueError as exc:
        # If the degree is too small, explain the issue and recover cleanly.
        print(exc)
        print("Using default t = 3.")
        tree = BTree(t=3)

    # Keep showing the menu until the user chooses Exit.
    while True:
        # Display all operations required by the assignment.
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

        # Read the user's menu choice as text.
        choice = input("Choose an option: ").strip()

        if choice == "1":
            # Load records from a text file. Pressing Enter uses students.txt.
            filename = input("Enter filename (default students.txt): ").strip() or "students.txt"
            try:
                inserted = load_into_tree(tree, filename)
                print(f"Loaded {inserted} new records into the B-tree.")
            except (FileNotFoundError, ValueError) as exc:
                # File and parsing problems are shown without crashing.
                print(f"Error: {exc}")

        elif choice == "2":
            # Display the actual B-tree shape, not just sorted records.
            print("\nB-tree structure:")
            tree.display()

        elif choice == "3":
            # Manually insert one student record.
            student_id = prompt_int("Student id: ")
            if student_id is None:
                # Return to the menu after invalid input.
                continue
            name = input("Student name: ").strip()
            gpa = prompt_float("GPA: ")
            if gpa is None:
                continue

            # Insert the new record. The B-tree rejects duplicate ids.
            if tree.insert(StudentRecord(student_id, name, gpa)):
                print("Student inserted.")
            else:
                print("That id already exists. Insert canceled.")

        elif choice == "4":
            # Generate and insert five random students.
            added = insert_random_students(tree, 5)
            print("Inserted these random students:")
            print_records(added)

        elif choice == "5":
            # Delete one student by primary key.
            student_id = prompt_int("Student id to delete: ")
            if student_id is None:
                continue
            if tree.delete(student_id):
                print("Student deleted.")
            else:
                print("Student id not found.")

        elif choice == "6":
            # Delete twenty random students, or fewer if the tree has less
            # than twenty records.
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
            record = tree.search(student_id)
            if record:
                print("Found:")
                print_records([record])
            else:
                print("Student id not found.")

        elif choice == "8":
            # Traversal prints all records sorted by id, which demonstrates the
            # B-tree's sorted ordering.
            print_records(tree.traverse())

        elif choice == "9":
            # End the interactive loop and quit the program.
            print("Goodbye.")
            break

        else:
            # Handle menu choices outside 1 through 9.
            print("Invalid option. Please choose 1 through 9.")


if __name__ == "__main__":
    # This makes the file executable as a script. The menu will not run if this
    # file is imported into a separate test script.
    menu()
