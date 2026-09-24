# Build fixture

This fixture proves that the publication pipeline can render Markdown,
inject a semantic figure, render semantic callouts and replaceable image
slots, and carry a rights notice into the publication.

The inspection sample has two practical limitations: its outline varies by
model, and the supplier's latest revision has not been checked.

```reportkit redflag
title: Weak
content: The inspection interval relies on a supplier revision that is not yet verified.
```

```reportkit tipnote
title: Strong
content: Compare the sample with the supplier's revision record before setting the interval.
```

The locally drawn object below exercises a supplied image slot.

[[REPORTKIT-IMAGE:img:fixture-object]]

The absent field photograph exercises the draft placeholder and can be
replaced at its declared asset path once a licensable image is selected.

[[REPORTKIT-IMAGE:img:field-photo]]

[[REPORTKIT-VISUAL:fig:fixture-flow]]
