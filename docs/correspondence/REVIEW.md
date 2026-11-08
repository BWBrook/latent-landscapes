# Review scope and provenance

This is a reviewed historical snapshot of discussion 87, the integrated Paper 1 development and numerical-method review, through message 2999 (8 November 2026). Codex (GPT-6.1 Sol) extended the content review to message 2999 on 8 November 2026, retaining every preceding review, clearing, redaction and withholding decision. The previous extension to messages 2906 and 2916 was recorded by Codex (GPT-6) on 6 November 2026. Of discussion 87's 38 messages, thirty-seven message bodies are retained with the redactions below; message 2814 is withheld in full.

The exporter writes the whole project. The other five discussions therefore retain their attribution and message placeholders, but all 121 bodies are withheld as outside this review's scope. Their presence in the index does not imply content review. This snapshot is not a complete public archive of the project.

The discussion deliberately preserves proposals, disagreements, errors, withdrawals and corrections. Publication here neither endorses every historical statement nor changes the status of a scientific claim. Later review messages qualify earlier interpretations, including the spatial-confounding explanation, the survivor-selected baseline comparison, calibration proposals and the likelihood representation. The exchange in messages 2890 and 2896 reviews the final development-challenge report and a prospective procedure amendment after outcomes were seen. It preserves the disagreement over qualification, corrections to the integration-screen interpretation, the descriptive contact-rule counterfactual and the unresolved solver witnesses. This does not retrospectively change the frozen challenge gates or establish readiness for rule training. Consult [the procedure review](../paper1-procedure-review-2026-11-05.md) for the subsequent evidence and proposed bounded diagnosis.

Messages 2897 and 2901 record the dependent sprint proposal and Codex's revision, including prospective review timing, deterministic numerical-score semantics, retention of all six truths and cost/precision qualifications. The public PBS scaling proposal remains, with private host names and routing recommendations redacted. This exchange records planning, not a launched sprint or campaign; validation remains behind the stated review and reconciliation boundary. See [the revised sprint plan](../paper1-sprints-2026-11-05.md).

Message 2906 hands over Sprint 1's candidate procedure, experiment packet and local evidence, with the unfinished compute-node pilot and proposed cost reductions explicit. Message 2916 records Sprint 2's independent entry review, numerical repairs, retained scientific scope, prospective qualification amendment and offline execution pipeline. It reports local verification and two historical diagnostics, not completed qualification or Sprint 2. The original proposals and subsequent corrections remain visible; validation stays closed and training has separate unresolved scientific gates. See [the Sprint 2 entry record](../paper1-sprint2-entry-2026-11-06.md).

Message 2999 records the completed two-case historical compute-node portability pilot, its independent audit, measured wall/CPU/memory costs and the retained walltime-interrupted attempt. It explicitly limits agreement to exact shared profile nodes and the eight complete confidence sets; it does not establish fresh qualification, scaling or calibration. The next bank-only resource measurement and the continuing training/validation gates remain explicit. The proposed distribution-free KL construction remains unadopted. See [the pilot evidence](../evidence/paper1-sprint2-pilot-2026-11-08/).

Redactions and withholding:

- Message 2814: the entire infrastructure/security-operations report is replaced by an explicit withheld placeholder.
- Messages 2713, 2722 and 2754: private host-selection/access-route passages are replaced by explicit inline withheld placeholders. Their scientific arguments remain.
- Message 2906: the operational portal-access request is replaced by an explicit inline placeholder; the unfinished pilot and scientific handover remain.
- Message 2897: the compute-routing recommendation is replaced by an explicit withheld placeholder. The scientific workload and cost discussion remains.
- Message 2855: the private bulk-archive location is replaced by an explicit withheld placeholder. Archive hashes and repository-relative evidence paths remain.
- Message 1877: the private questionnaire identifier is replaced by an explicit withheld placeholder. The recorded scientific direction remains.
- Listed machine names are replaced by `[compute host]`. The exporter also removes address, e-mail and personal home-directory patterns. These substitutions do not change reported numerical values.

No third-party copyrighted extract, collaborator personal correspondence or credential was identified in the 37 retained bodies. Quotations of Barry's project directions and of the agents' own proposals remain as part of the scientific collaboration record. Bibliographic references and public DOI links remain. Historical model labels are preserved exactly when supplied; missing labels are not inferred.

`publication.toml` records every cleared or withheld message and each additional redaction. `snapshot.json` records the exporter revision and SHA-256, message boundaries, source-content hashes and generated-file hashes. Source-content hashes use the existing canonical convention: UTF-8 JSON with `sort_keys=True`, `ensure_ascii=False` and `separators=(",", ":")`, without a trailing newline. The top-level keys are `thread` and `messages`; `thread` contains only `id`, `title`, `status`, and each message contains `id`, `author`, `model`, `kind`, `created_at`, `parent_id`, `body` (missing values become null). Messages retain board order. Read markers are excluded. The five unchanged thread hashes and the previous discussion-87 prefix through message 2916 reproduce exactly. All newly returned project messages were reviewed before retaining any new body; the sole new message was 2999 in discussion 87. Raw board content was held only in a private temporary review file, never added to this repository.

The standard export command is:

```sh
uv run --project ~/work/correspondence correspondence-export docs/correspondence/publication.toml
```

This command refreshes from the live board; it is not a frozen-data replay. Review every newly fetched message before committing a refresh, including messages without flagged terms. Term flags are a review aid, not a complete privacy test. Update the policy, review scope and snapshot hashes together. Do not clear a message solely because a previous message in the same discussion was cleared.

Verification completed: every generated discussion exactly matched a fresh rendering of the captured source using the recorded policy; all 159 message IDs were represented exactly once; 37 bodies were cleared and 122 withheld. The retained output passed scans for address/home-directory patterns, listed hosts, private archive paths, private routing terms and the newly withheld access request. All earlier redaction and withholding decisions remain. Source-content hashes, boundaries, counts and generated-file hashes were updated together. No board messages, read markers or statuses were changed.
