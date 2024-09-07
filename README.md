
# TODOs:
- sqlite orm:
  - enforce strict tables (for inflexible datatypes)
  - enforce foreign keys validation
  - add not null constraint on primary key (even though it's not necessary if you have STRICT and WITHOUT_ROWIDS features)
  - sqlite does not do unicode case folding, so better to disallow upper/lower entirely
    - what does that mean for case insensitive search?
  - make string literals use single quotes
  - columns with INTEGER PRIMARY KEY should also allow an AUTOINCREMENT option (maybe you expect results to be chronologically sorted by id idk)
