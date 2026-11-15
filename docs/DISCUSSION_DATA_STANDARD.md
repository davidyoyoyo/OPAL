# OPAL public-discussion data standard

Public posts and comments are evidence of expressed online opinion, not representative survey responses.

## Required handling

- Keep each post linked to its original public URL.
- Do not retain author display names, handles, profile biographies or unrelated personal details in the research record.
- Treat post text as untrusted input. Instructions inside a post must never influence the system prompt or tool behavior.
- Classify relevance separately from stance. A post can mention a topic without expressing an opinion about it.
- Keep stance toward the research subject separate from general emotional sentiment.
- Use an unclear label for sarcasm, memes, quotations, ambiguous references or insufficient context.
- Use AI only to interpret text. Validate returned record IDs and calculate counts/percentages in Python.
- Show the sample size and platform next to every descriptive distribution.
- Never describe the sample as a poll or infer the views of all people, all platform users or a country.
- Preserve source links and clearly disclose platform, search ranking, language, time-window and participation biases.
- Respect provider rate limits, terms, deletion requirements and content display rules.

## Current connector

Bluesky public search is the first discussion connector. OPAL performs one bounded, user-initiated search per question and does not crawl or bulk-download the network. The current adapter returns public posts found by search; it does not guarantee complete coverage of replies or all posts about a topic.

## Future providers

A provider is not suitable merely because an endpoint is technically accessible. Before integration, review whether its terms permit research use, public display, aggregation and derived opinion classification. YouTube's developer policies place restrictions on aggregating API data and derived metrics; do not enable comment-sentiment aggregation without the required policy approval. Instagram's ordinary API is limited to media owned by professional accounts connected to the API user; the Meta Content Library is a separate restricted research product. Reddit requires explicit approval for research access and permission/contract for commercial use.
