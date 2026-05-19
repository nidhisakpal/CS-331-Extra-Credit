# CS 331 B+ Tree Student Index

This project is a small database-style indexing program written in Python. It reads a student table from a text file and stores each row in a B+ tree using `id` as the primary key.

## Deliverables

- `main.py`: B+ tree implementation and menu-driven CLI
- `students.txt`: sample input file with 100 rows
- `README.md`: project explanation and instructions

## What Is a B+ Tree?

A B+ tree is a balanced search tree commonly used for database indexes. It is similar to a B-tree, but with one very important difference:

- Internal nodes store separator keys used for navigation.
- Full records are stored only in the leaf nodes.
- Leaf nodes are linked together from left to right.

The linked leaf level is especially useful for database range scans and sorted output.

For this project, the minimum degree `t` controls node size:

- Each node can store at most `2t - 1` keys.
- Each non-root node should store at least `t - 1` keys.
- When a leaf or internal node becomes too large, it is split.
- When deletion makes a node too small, it borrows from a sibling or merges with a sibling.
- The tree stays balanced because all leaf nodes remain at the same depth.

## Why B+ Trees Matter in Databases

B+ trees are widely used for database indexes. A database index lets the system find a row without scanning every row in the table.

In this project:

- The table columns are `id`, `studentname`, and `gpa`.
- The `id` column is treated as the primary key.
- The B+ tree uses `id` as the search key.
- Internal nodes guide the search.
- Leaf nodes store the full `StudentRecord` objects.
- Searching by `id` simulates using an index on a primary key.

This is useful because B+ trees keep keys sorted and reduce search, insert, and delete time compared to linear scanning through every record.

## Operations Implemented

The program supports:

- Loading records from a text file
- Displaying the B+ tree structure
- Displaying the linked leaf chain
- Inserting one student
- Inserting 5 randomly generated students
- Deleting one student by `id`
- Deleting 20 random students
- Searching by `id`
- Printing all records in sorted order by scanning the leaf level

## Input File Format

The sample file is `students.txt`.

Expected format:

```text
id,studentname,gpa
1,Emma Johnson,3.82
2,Liam Smith,3.45
```

The parser also tries to handle comma-separated, tab-separated, and whitespace-separated rows.

When loading from a file, the program sorts the records by `id` before building
the B+ tree. This makes the initial index deterministic: the same set of rows
creates the same B+ tree even if the input file is shuffled.

## How to Run

Open a terminal in this project folder and run:

```bash
python main.py
```

If your system uses `python3`, run:

```bash
python3 main.py
```

When prompted for the B+ tree minimum degree, enter a number such as `3`. If you enter an invalid value, the program uses the default value `3`.

## Menu

```text
1. Load data from file
2. Display B+ tree
3. Insert a student
4. Insert 5 random students
5. Delete a student by id
6. Delete 20 random students
7. Search by id
8. Print all records in sorted order
9. Exit
```

## Example Session

```text
CS 331 B+ Tree Student Index
Enter minimum degree t for the B+ tree (default 3): 3

Menu
1. Load data from file
...
Choose an option: 1
Enter filename (default students.txt):
Loaded 100 new records into the B+ tree.

Choose an option: 7
Student id to search for: 25
Found:
  ID | Student Name             | GPA
---------------------------------------
  25 | Elizabeth Harris         | 3.97
```

## B+ Tree Insert

Insertion descends through internal separator keys until it reaches the correct leaf. The new record is inserted into that leaf in sorted order. If the leaf becomes too large, it splits into two leaves, and the first key of the new right leaf becomes a separator in the parent. If the parent overflows, internal nodes split upward as needed.

For the menu option that loads the original table from a file, the records are
sorted by primary key before insertion. This matches how a database would build
an index from an existing table and prevents the initial tree display from
depending on the row order in the text file.

## B+ Tree Search

Search starts at the root and uses separator keys to choose the correct child at each internal node. Eventually, the search reaches one leaf node. Since all full records are stored in leaves, the program checks only that leaf for the requested `id`.

## B+ Tree Delete

Deletion removes the record from a leaf node. If the leaf still has enough keys, the tree only refreshes separator keys. If the leaf has too few keys, the tree borrows from a sibling when possible. If borrowing is not possible, it merges with a sibling and updates the parent. This keeps the B+ tree balanced.

## Sorted Traversal

Sorted traversal starts at the leftmost leaf and follows each leaf's `next` pointer. This is different from a regular B-tree traversal and is one reason B+ trees are useful in database systems.

## Project Connection to Database Systems

This project models the core idea of a database primary-key index. Instead of searching row by row, the program uses a B+ tree keyed by `id`. This is similar to how a database can use a primary-key index to quickly locate a row.

B+ trees are a strong fit for databases because they:

- Keep keys sorted
- Store full records at the leaf level
- Link leaves for efficient sorted scans and range queries
- Stay balanced as data changes
- Support efficient search, insertion, and deletion
- Avoid the cost of scanning every table row for primary-key lookups
