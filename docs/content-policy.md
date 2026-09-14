# Content and licensing policy

MeroGuru discovers and links to external learning resources. It does not treat public
availability as permission to copy or republish content.

## YouTube

- Discovery and metadata (title, description, channel, duration, embeddability) use
  only the official YouTube Data API.
- Videos are embedded/linked for the learner to watch directly on YouTube; MeroGuru
  never downloads video, audio, or captions.
- Transcript-based lesson content only uses text supplied through one of these modes:
  - **User-provided transcript** — you paste in text you already have the right to use.
  - **Creator-authorized transcript** — a transcript the video's own creator has shared
    for this purpose.
  - **Openly licensed** — content explicitly licensed for reuse (e.g. Creative Commons).
- Everything else stays **metadata-only**: the AI can still build a lesson around the
  title/description, but does not process caption text it has no rights to.

## MediaWiki / Wikipedia

Uses the official MediaWiki Action API. Article title, URL, section, revision, and
retrieval time are stored for attribution.

## Manual and user-provided content

You can add any URL or paste your own notes. Every stored resource records a
`content_access` / permission basis; nothing is silently reclassified as "reusable"
just because it was publicly reachable.

## Every resource records

- Provider, original URL, author/publisher when known
- Content type and language
- License or access classification
- Retrieval date
- Processing permission basis

If you believe a resource is misclassified or shouldn't be recommended, remove it from
your plan and, if you're running a multi-person deployment in the future, report it
through the admin tooling.
