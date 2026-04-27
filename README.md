# CS 331 B-tree Student Index

This project is a small database-style indexing program written in Python. It reads a student table from a text file and stores each row in a B-tree using `id` as the primary key.

## Deliverables

- `main.py`: B-tree implementation and menu-driven CLI
- `students.txt`: sample input file with 100 rows
- `README.md`: project explanation and instructions

## What Is a B-tree?

A B-tree is a balanced search tree designed to keep keys sorted and make search, insert, and delete operations efficient. Unlike a binary search tree, each B-tree node can store multiple keys and can have multiple children.

For a minimum degree `t`:

- Each node can store at most `2t - 1` keys.
- Each non-root node stores at least `t - 1` keys.
- When a node becomes full during insertion, it is split around its middle key.
- The tree stays balanced because all leaf nodes remain at the same depth.

## Why B-trees Matter in Databases

B-trees are commonly used for database indexes. A database index lets the system find a row without scanning every row in the table.

In this project:

- The table columns are `id`, `studentname`, and `gpa`.
- The `id` column is treated as the primary key.
- The B-tree stores each `id` as a key.
- Each key maps to the full `StudentRecord`.
- Searching by `id` simulates using an index on a primary key.

This is useful because B-trees keep data sorted and reduce search, insert, and delete time compared to linear scanning through every record.

## Operations Implemented

The program supports:

- Loading records from a text file
- Displaying the B-tree structure
- Inserting one student
- Inserting 5 randomly generated students
- Deleting one student by `id`
- Deleting 20 random students
- Searching by `id`
- Printing all records in sorted order by `id`

## Input File Format

The sample file is `students.txt`.

Expected format:

```text
id,studentname,gpa
1,Emma Johnson,3.82
2,Liam Smith,3.45
```

The parser also tries to handle comma-separated, tab-separated, and whitespace-separated rows.

## How to Run

Open a terminal in this project folder and run:

```bash
python main.py
```

If your system uses `python3`, run:

```bash
python3 main.py
```

When prompted for the B-tree minimum degree, press Enter after typing a number such as `3`. If you enter an invalid value, the program uses the default value `3`.

## Menu

```text
1. Load data from file
2. Display B-tree
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
CS 331 B-tree Student Index
Enter minimum degree t for the B-tree (default 3): 3

Menu
1. Load data from file
...
Choose an option: 1
Enter filename (default students.txt):
Loaded 100 new records into the B-tree.

Choose an option: 7
Student id to search for: 25
Found:
  ID | Student Name             | GPA
---------------------------------------
  25 | Elizabeth Harris         | 3.97
```

## B-tree Insert

Insertion starts at the root. If the root is full, the program splits it first. Then it descends into the correct child. Any full child is split before inserting into it. This keeps every node within the maximum key limit.

## B-tree Search

Search compares the target `id` with the sorted keys in a node. If the key is found, the matching `StudentRecord` is returned. If not, the search continues into the child where that key would belong.

## B-tree Delete

Deletion handles three main cases:

- If the key is in a leaf node, it is removed directly.
- If the key is in an internal node, it is replaced by a predecessor or successor when possible.
- If needed, children are borrowed from or merged so the B-tree rules remain valid.

## Sorted Traversal

The traversal visits children and keys in sorted order, so printing all records displays the table ordered by `id`.

## Project Connection to Database Systems

This project models the core idea of a database index. Instead of searching row by row, the program uses a B-tree keyed by `id`. This is similar to how a database can use a primary-key index to quickly locate a row.

B-trees are a good fit for databases because they:

- Keep keys sorted
- Stay balanced as data changes
- Support efficient search, insertion, and deletion
- Avoid the cost of scanning every table row for primary-key lookups
