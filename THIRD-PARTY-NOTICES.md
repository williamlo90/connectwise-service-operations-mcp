# Third-party notices

The root [LICENSE](LICENSE) applies only to original project materials owned by William. Third-party rights remain unchanged.

- **Qwen3 0.6B:** Apache-2.0. The exact license text from the pinned model layer is retained at [docs/licenses/QWEN3-APACHE-2.0.txt](docs/licenses/QWEN3-APACHE-2.0.txt). Model and license-layer hashes are recorded in [contracts/local-model.json](contracts/local-model.json) and the [dependency inventory](docs/evidence/release-dependencies.json). Model weights are not committed to this repository.
- **Python and JavaScript dependencies:** retain their own package licenses. Versions are pinned in `backend/requirements.lock` and `client/package-lock.json`; recorded metadata is in the [dependency inventory](docs/evidence/release-dependencies.json). Missing license metadata is not permission to remove a dependency's license obligations.
- **Container base images and bundled runtime components:** retain their upstream licenses. Images are referenced, not redistributed as repository files. The application inventory does not enumerate all operating-system package notices; inspect those components before redistributing an image.
- **ConnectWise, OpenAI, Ollama, Azure and other product names:** identify referenced products. This project is independent and does not imply endorsement or official certification.

The repository's restrictive notice does not make third-party dependencies or the Qwen model proprietary. Review the applicable upstream terms for any redistribution beyond this portfolio repository.
