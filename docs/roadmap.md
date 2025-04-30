## 🧙 About

**Sourcerer** is created to unify cloud storage exploration under a developer-friendly interface. Whether you're managing S3 buckets or navigating GCP storage, Sourcerer brings clarity, control to your data workflows.

Our roadmap unveils the features, improvements, and integrations designed to empower engineers and DevOps adventurers. Got a feature request in mind? Open a github discussion!

---

## 🗺️ The Roadmap

- [ ] **Initial release** 

- ✅ **Multi-cloud storage viewing** – Navigate files and folders from:
  - ✅ Google Cloud Storage (GCS)
    - ✅ Credentials json
  - ✅ S3-compatible storages (e.g. AWS S3, MinIO, etc.)
    - ✅ Access Key/Secret Key pair
    - ✅ Profile name
  - [] Azure Blob Storage (planned)

- [ ] **Storage actions support** – Perform basic operations with ease:
  - [ ] View storage metadata
  - ✅ List buckets/objects
  - ✅ Download files
  - ✅ Upload files
  - ✅ Delete objects
  - [ ] Rename / move objects

- [ ] **Bookmarking** – Save frequently visited locations across storage accounts for quick teleportation.

- ✅ **File preview** – View contents of text files (e.g., logs, JSON, YAML) directly in the terminal UI.

- [ ] **Plugin system** – Extend Sourcerer with your own storage providers

- [ ] **Keyboard shortcuts** – Improve navigation and productivity with magic keybindings.

- [ ] **Keyboard navigation** – Improve navigation using keyboard only.

- [ ] **Error and retry handling** – Automatic retries for flaky cloud responses and graceful error dialogs.

- [ ] **Cross-provider copy** – Move files between GCS and S3 in one unified action.

- [ ] **Logging** – Keep detailed logs for your Sourcerer actions and errors.

- ✅ **Encrypted config store** – Store access keys securely with local encryption.

- [ ] **Auto-updater** – Keep users' apps upgraded with the latest features.

- [ ] **Register storages** – Some storage providers may not return storages if the user is not a creator (but still has access). This feature will allow user to register storages manually.