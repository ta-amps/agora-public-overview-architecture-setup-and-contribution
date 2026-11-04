# Maintaining Agora

Agora is a public guide and dated status record. Keep product behavior in its owning repository. Do not add a scheduler, importer, model caller, credential store or competing noun/verb implementation here.

For a status update, check the relevant repository revision, its CI, the deployed interface when applicable, and the evidence behind each capability claim. Record the observation date and exact revision in `status.json`. Update the status report and README together. Keep historical evidence dated and retain the limits of failed, skipped or narrow tests.

Distinguish implemented code, deployed behavior, observed results and proposed work. A green CI run is evidence about its checks; a byte match identifies the executable; neither establishes universal correctness. A record, category label or schema-valid example is not admission evidence.

Publish only approved public facts and synthetic examples. Keep credentials, internal notes, raw session transcripts, private identities and infrastructure account details out of the repository. Link to public evidence in the owning repository when available.

Run `make check` before committing. The checker validates snapshot structure, revision formats, internal consistency, local Markdown links and common accidental secret/path patterns. It does not contact live services or make provider calls, and it cannot detect every private fact. Review the diff before publication.

Use a pull request for future changes, with a concrete description of the changed behavior or evidence and relevant validation. Preserve history and avoid force pushes. Public snapshot updates should make uncertainty easier to find, not hide it behind a new date.
