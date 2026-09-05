"""The bibliographic indexes, one module each.

Every module here holds the same three things in the same order: the wire
records that service actually sends, the calls that fetch them, and one
`record` function crossing a wire record into the shared `Work`. Nothing in
one index module imports another, so adding a fourth index adds one file.
"""
