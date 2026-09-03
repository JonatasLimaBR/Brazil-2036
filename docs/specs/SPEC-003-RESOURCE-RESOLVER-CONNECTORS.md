# SPEC-003 — Resource Resolver & Connectors
Supported initial resource types: CSV, JSON, ZIP, XLSX, REST, CKAN/OData where required.
Connector interface: discover, metadata, download, validate, checkpoint.
HTTP failures use bounded retries and are recorded. Checkpoint prevents duplicate reload when resource hash unchanged.
