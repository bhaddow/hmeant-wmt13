hmeant-wmt13
=============

This project contains the data collected for the following paper:

```
@InProceedings{birch-EtAl:2013:WMT,
  author    = {Birch, Alexandra  and  Haddow, Barry  and  Germann, Ulrich  and  Nadejde, Maria  and  Buck, Christian  and  Koehn, Philipp},
  title     = {The Feasibility of {HMEANT} as a Human {MT} Evaluation Metric},
  booktitle = {Proceedings of the Eighth Workshop on Statistical Machine Translation},
  month     = {August},
  year      = {2013},
  address   = {Sofia, Bulgaria},
  publisher = {Association for Computational Linguistics},
  pages     = {52--61},
  url       = {http://www.aclweb.org/anthology/W13-2203}
}
```

All the data is contained in the `data` directory, in a flat-file, tab separated, database format. The script
`annotation.py` can be used to access the data - running it will iterate through the annotations displaying them 
one at a time. Alternatively, the script can be imported to provide programmatic access to the annotations.

The tables in the database are as follows:

`sentences`
Contains an entry for each hypothesis and reference in the corpus. Each sentence record has a unique `id`,
a `language` (either de or en), a `segment` and a `number` within that segment. The sentences were divided up into
segments to give the annotators smaller units to work on. The `version` column specifies whether the sentence
was a hypothesis (00), a phrase-based output (01), a syntax-based output (02) or a rule-based output (03). The
last column shows the sentence length.

`sentences_text`  
This is the same as `sentences`, except that the last column is the text of the sentence. It is a separate table
because having the sentence text in the table makes processing more difficult.

`annotations`
Contains a record for each annotation of each sentence. Each sentence was annotated by two annotators. The
fields in this file are the `id`, the corresponding `sentence_id`, the annotator and the corresponding reference
annotation `ref_id`. The last field is a key into the `annotations` table, and requires some explanation. In
the annotation, the annotator first annotated the reference, then the corresponding hypotheses (system outputs).
When they started annotating the system outputs, a copy was made of the reference annotation, and the copy
linked with the system output annotation. The field `ref_id` is non-null for any hypothesis annotation, and 
provides a link to the corresponding reference annotation.

`actions`
This table shows all the actions (aka frames) annotated. The three columns are the primary key (`id`), a foreign
key into the `annotations` table, and the token number of the frame head.

`slots`
This shows the annotated slots, with each record containing a primary key (`id`), a foreign key into the
`actions` table, a type, and a sequence of tokens (always continuous).

`action_aligns`
These link an action in the reference with an action in a corresponding hypothesis. Aside from the primary
key (`id`) this has foreign keys into the `actions` table, and a type (full or partial).

`slot_aligns`
Similar to the `action_aligns`, these show the links between entries in the `slots` table.
