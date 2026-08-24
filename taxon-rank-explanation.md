# LifeSQL Taxon Rank Specification

LifeSQL preserves the complete set of taxonomic ranks present in the Catalogue of Life XR dataset.

Ranks are represented internally by integer IDs rather than repeated strings in the database.

The integer IDs are stable LifeSQL identifiers. The application may provide a human-readable name for each ID.

## Rank Mapping

| ID | Catalogue of Life rank |
| -: | ---------------------- |
|  1 | domain                 |
|  2 | kingdom                |
|  3 | subkingdom             |
|  4 | infrakingdom           |
|  5 | realm                  |
|  6 | phylum                 |
|  7 | subphylum              |
|  8 | infraphylum            |
|  9 | parvphylum             |
| 10 | gigaclass              |
| 11 | megaclass              |
| 12 | superclass             |
| 13 | class                  |
| 14 | subclass               |
| 15 | infraclass             |
| 16 | subterclass            |
| 17 | order                  |
| 18 | suborder               |
| 19 | infraorder             |
| 20 | parvorder              |
| 21 | nanorder               |
| 22 | superorder             |
| 23 | series zoology         |
| 24 | section zoology        |
| 25 | superfamily            |
| 26 | epifamily              |
| 27 | family                 |
| 28 | infrafamily            |
| 29 | subfamily              |
| 30 | tribe                  |
| 31 | infratribe             |
| 32 | supertribe             |
| 33 | subtribe               |
| 34 | genus                  |
| 35 | subgenus               |
| 36 | infrageneric name      |
| 37 | section botany         |
| 38 | subsection botany      |
| 39 | species                |
| 40 | species aggregate      |
| 41 | subspecies             |
| 42 | proles                 |
| 43 | variety                |
| 44 | subvariety             |
| 45 | form                   |
| 46 | subform                |
| 47 | forma specialis        |
| 48 | morph                  |
| 49 | natio                  |
| 50 | lusus                  |
| 51 | aberration             |
| 52 | mutatio                |
| 53 | infraspecific name     |
| 54 | other                  |

## Database Representation

The `taxa.rank` column stores the integer ID.

For example:

* `34` = genus
* `39` = species
* `41` = subspecies
* `43` = variety

The application maintains the mapping between the integer ID and the Catalogue of Life rank name.

## Source

The rank vocabulary is derived from the `dwc:taxonRank` values present in the Catalogue of Life XR 2026-07-17 `Taxon.tsv` dataset used by LifeSQL.

The mapping should only be changed deliberately if the underlying LifeSQL taxonomy specification changes.
