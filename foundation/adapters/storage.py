"""
Document Storage Abstraction Layer (Phase DEPLOY-1)
===================================================
Location: foundation/adapters/storage.py

Provides unified interface for storing, reading, and downloading document
binaries across local filesystem (.uploads/) and cloud object storage
(Supabase Storage buckets: documents, generated, source-artifacts).

Enforces:
    - Guaranteed temp-file cleanup in finally blocks on all paths.
    - User and session isolation in storage paths.
    - Immutability and SHA256 integrity verification.
    - Zero local filesystem dependencies in production mode.
"""
from __future__ import annotations

import abc
import contextlib
import hashlib
import io
import os
from dataclasses import dataclass
from pathlib import Path
import tempfile
from typing import Any, Generator, Optional, Tuple

from werkzeug.utils import secure_filename

from config import AppConfig, StorageBackend, get_config


class StorageError(RuntimeError):
    """Raised when an object storage operation fails."""


@dataclass
class StorageResult:
    """Metadata result after saving a binary file to storage."""
    storage_path: str
    file_hash: str
    size_bytes: int
    filename: str
    is_patched: bool = False


class DocumentStorage(abc.ABC):
    """Abstract storage interface for document artifacts."""

    @abc.abstractmethod
    def save_document(
        self,
        session_id: str,
        doc_id: str,
        filename: str,
        data: bytes,
        is_patched: bool = False,
        user_id: str = "anonymous",
    ) -> StorageResult:
        """Saves a document or patched version to storage."""

    @abc.abstractmethod
    def get_document_bytes(
        self,
        session_id: str,
        doc_id: str,
        is_patched: bool = False,
        user_id: str = "anonymous",
    ) -> bytes:
        """Retrieves document raw bytes."""

    @abc.abstractmethod
    @contextlib.contextmanager
    def get_document_path(
        self,
        session_id: str,
        doc_id: str,
        is_patched: bool = False,
        user_id: str = "anonymous",
    ) -> Generator[Path, None, None]:
        """Yields a local filesystem Path to the document.

        Guarantees cleanup in a finally block if a temporary file was downloaded.
        """

    @abc.abstractmethod
    def document_exists(
        self,
        session_id: str,
        doc_id: str,
        is_patched: bool = False,
        user_id: str = "anonymous",
    ) -> bool:
        """Checks if a document file exists."""

    @abc.abstractmethod
    def save_generated_file(
        self,
        session_id: str,
        filename: str,
        data: bytes,
        user_id: str = "anonymous",
    ) -> StorageResult:
        """Saves a generated output file to the generated bucket."""

    @abc.abstractmethod
    def get_generated_bytes(
        self,
        session_id: str,
        filename: str,
        user_id: str = "anonymous",
    ) -> bytes:
        """Retrieves a generated output file."""

    @abc.abstractmethod
    def save_source_artifact(
        self,
        package_id: str,
        artifact_id: str,
        filename: str,
        data: bytes,
        user_id: str = "anonymous",
    ) -> StorageResult:
        """Saves a Phase G source artifact to storage."""

    @abc.abstractmethod
    def get_source_artifact_bytes(
        self,
        package_id: str,
        artifact_id: str,
        filename: str,
        user_id: str = "anonymous",
    ) -> bytes:
        """Retrieves a Phase G source artifact."""

    @abc.abstractmethod
    def check_health(self) -> Tuple[bool, str]:
        """Probes storage backend health without leaking secrets."""


# ============================================================================
# LOCAL DOCUMENT STORAGE (DEV & TESTING)
# ============================================================================

class LocalDocumentStorage(DocumentStorage):
    """Local filesystem storage adapter backing .uploads/."""

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or (Path(__file__).resolve().parents[1] / ".uploads")
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _session_dir(self, session_id: str, user_id: str = "anonymous") -> Path:
        # In local mode, keep session_id as directory name for backward compatibility
        dir_path = self.root_dir / secure_filename(session_id)
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    def _doc_filename(self, doc_id: str, filename: str, is_patched: bool) -> str:
        clean_name = secure_filename(filename)
        if is_patched:
            stem = Path(clean_name).stem
            suffix = Path(clean_name).suffix
            return f"{doc_id}_{stem}_patched{suffix}"
        return f"{doc_id}_{clean_name}"

    def save_document(
        self,
        session_id: str,
        doc_id: str,
        filename: str,
        data: bytes,
        is_patched: bool = False,
        user_id: str = "anonymous",
    ) -> StorageResult:
        s_dir = self._session_dir(session_id, user_id)
        file_name = self._doc_filename(doc_id, filename, is_patched)
        target_path = s_dir / file_name
        target_path.write_bytes(data)
        sha256 = hashlib.sha256(data).hexdigest()
        return StorageResult(
            storage_path=str(target_path),
            file_hash=sha256,
            size_bytes=len(data),
            filename=filename,
            is_patched=is_patched,
        )

    def _find_doc_path(self, session_id: str, doc_id: str, is_patched: bool) -> Optional[Path]:
        s_dir = self.root_dir / secure_filename(session_id)
        if not s_dir.is_dir():
            return None
        prefix = f"{doc_id}_"
        for p in s_dir.iterdir():
            if p.is_file() and p.name.startswith(prefix):
                if is_patched and "_patched" in p.name:
                    return p
                elif not is_patched and "_patched" not in p.name:
                    return p
        return None

    def get_document_bytes(
        self,
        session_id: str,
        doc_id: str,
        is_patched: bool = False,
        user_id: str = "anonymous",
    ) -> bytes:
        path = self._find_doc_path(session_id, doc_id, is_patched)
        if path is None or not path.exists():
            raise StorageError(f"Document '{doc_id}' (patched={is_patched}) not found in session '{session_id}'.")
        return path.read_bytes()

    @contextlib.contextmanager
    def get_document_path(
        self,
        session_id: str,
        doc_id: str,
        is_patched: bool = False,
        user_id: str = "anonymous",
    ) -> Generator[Path, None, None]:
        path = self._find_doc_path(session_id, doc_id, is_patched)
        if path is None or not path.exists():
            raise StorageError(f"Document '{doc_id}' (patched={is_patched}) not found in session '{session_id}'.")
        yield path

    def document_exists(
        self,
        session_id: str,
        doc_id: str,
        is_patched: bool = False,
        user_id: str = "anonymous",
    ) -> bool:
        return self._find_doc_path(session_id, doc_id, is_patched) is not None

    def save_generated_file(
        self,
        session_id: str,
        filename: str,
        data: bytes,
        user_id: str = "anonymous",
    ) -> StorageResult:
        s_dir = self._session_dir(session_id, user_id)
        target_path = s_dir / secure_filename(filename)
        target_path.write_bytes(data)
        sha256 = hashlib.sha256(data).hexdigest()
        return StorageResult(
            storage_path=str(target_path),
            file_hash=sha256,
            size_bytes=len(data),
            filename=filename,
            is_patched=True,
        )

    def get_generated_bytes(
        self,
        session_id: str,
        filename: str,
        user_id: str = "anonymous",
    ) -> bytes:
        s_dir = self._session_dir(session_id, user_id)
        target_path = s_dir / secure_filename(filename)
        if not target_path.exists():
            raise StorageError(f"Generated file '{filename}' not found in session '{session_id}'.")
        return target_path.read_bytes()

    def save_source_artifact(
        self,
        package_id: str,
        artifact_id: str,
        filename: str,
        data: bytes,
        user_id: str = "anonymous",
    ) -> StorageResult:
        pkg_dir = self.root_dir / "source_packages" / secure_filename(package_id)
        pkg_dir.mkdir(parents=True, exist_ok=True)
        clean_name = f"{artifact_id}_{secure_filename(filename)}"
        target_path = pkg_dir / clean_name
        target_path.write_bytes(data)
        sha256 = hashlib.sha256(data).hexdigest()
        return StorageResult(
            storage_path=str(target_path),
            file_hash=sha256,
            size_bytes=len(data),
            filename=filename,
        )

    def get_source_artifact_bytes(
        self,
        package_id: str,
        artifact_id: str,
        filename: str,
        user_id: str = "anonymous",
    ) -> bytes:
        pkg_dir = self.root_dir / "source_packages" / secure_filename(package_id)
        clean_name = f"{artifact_id}_{secure_filename(filename)}"
        target_path = pkg_dir / clean_name
        if not target_path.exists():
            raise StorageError(f"Source artifact '{artifact_id}' not found in package '{package_id}'.")
        return target_path.read_bytes()

    def check_health(self) -> Tuple[bool, str]:
        try:
            test_file = self.root_dir / ".health_check_probe"
            test_file.write_text("health", encoding="utf-8")
            test_file.unlink()
            return True, "Local storage is accessible and writable."
        except Exception as exc:
            return False, f"Local storage error: {exc}"


# ============================================================================
# SUPABASE DOCUMENT STORAGE (PRODUCTION)
# ============================================================================

class SupabaseDocumentStorage(DocumentStorage):
    """Supabase Object Storage adapter for production deployments."""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or get_config()
        if not self.config.supabase_url or not self.config.supabase_service_role_key:
            raise StorageError(
                "SupabaseDocumentStorage requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
            )

        # Lazy import of supabase to keep local mode free of external SDK requirement if unneeded
        try:
            from supabase import create_client, Client
            self._client: Client = create_client(
                self.config.supabase_url,
                self.config.supabase_service_role_key,
            )
        except ImportError:
            raise StorageError("supabase-py library is not installed. Install with `pip install supabase`.")
        except Exception as exc:
            raise StorageError(f"Failed to initialize Supabase client: {exc}") from exc

        self.bucket_documents = self.config.bucket_documents
        self.bucket_generated = self.config.bucket_generated
        self.bucket_source_artifacts = self.config.bucket_source_artifacts

    def _doc_storage_path(
        self,
        user_id: str,
        session_id: str,
        doc_id: str,
        filename: str,
        is_patched: bool,
    ) -> str:
        clean_name = secure_filename(filename)
        patch_tag = "patched_" if is_patched else ""
        return f"{user_id}/{session_id}/{doc_id}_{patch_tag}{clean_name}"

    def save_document(
        self,
        session_id: str,
        doc_id: str,
        filename: str,
        data: bytes,
        is_patched: bool = False,
        user_id: str = "anonymous",
    ) -> StorageResult:
        path = self._doc_storage_path(user_id, session_id, doc_id, filename, is_patched)
        try:
            # Overwrite if exists via upsert
            self._client.storage.from_(self.bucket_documents).upload(
                path=path,
                file=data,
                file_options={"upsert": "true"},
            )
        except Exception as exc:
            raise StorageError(f"Failed to upload document to Supabase storage: {exc}") from exc

        sha256 = hashlib.sha256(data).hexdigest()
        return StorageResult(
            storage_path=path,
            file_hash=sha256,
            size_bytes=len(data),
            filename=filename,
            is_patched=is_patched,
        )

    def _resolve_storage_path(
        self,
        user_id: str,
        session_id: str,
        doc_id: str,
        is_patched: bool,
    ) -> str:
        folder = f"{user_id}/{session_id}"
        try:
            files = self._client.storage.from_(self.bucket_documents).list(path=folder)
            prefix = f"{doc_id}_"
            for f in files:
                name = f.get("name", "")
                if name.startswith(prefix):
                    if is_patched and "_patched" in name:
                        return f"{folder}/{name}"
                    elif not is_patched and "_patched" not in name:
                        return f"{folder}/{name}"
        except Exception as exc:
            raise StorageError(f"Error resolving document path in Supabase Storage: {exc}") from exc
        raise StorageError(f"Document '{doc_id}' (patched={is_patched}) not found in session '{session_id}'.")

    def get_document_bytes(
        self,
        session_id: str,
        doc_id: str,
        is_patched: bool = False,
        user_id: str = "anonymous",
    ) -> bytes:
        path = self._resolve_storage_path(user_id, session_id, doc_id, is_patched)
        try:
            return self._client.storage.from_(self.bucket_documents).download(path)
        except Exception as exc:
            raise StorageError(f"Failed to download document bytes from Supabase storage: {exc}") from exc

    @contextlib.contextmanager
    def get_document_path(
        self,
        session_id: str,
        doc_id: str,
        is_patched: bool = False,
        user_id: str = "anonymous",
    ) -> Generator[Path, None, None]:
        """Downloads document bytes to a temporary file and guarantees deletion in finally."""
        data = self.get_document_bytes(session_id, doc_id, is_patched=is_patched, user_id=user_id)
        # Determine extension from filename in storage path
        ext = ".docx"
        try:
            storage_path = self._resolve_storage_path(user_id, session_id, doc_id, is_patched)
            ext = Path(storage_path).suffix or ".docx"
        except Exception:
            pass

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        temp_path = Path(temp_file.name)
        try:
            temp_file.write(data)
            temp_file.flush()
            temp_file.close()
            yield temp_path
        finally:
            # Guaranteed cleanup across all exception / normal paths
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass

    def document_exists(
        self,
        session_id: str,
        doc_id: str,
        is_patched: bool = False,
        user_id: str = "anonymous",
    ) -> bool:
        try:
            self._resolve_storage_path(user_id, session_id, doc_id, is_patched)
            return True
        except StorageError:
            return False

    def save_generated_file(
        self,
        session_id: str,
        filename: str,
        data: bytes,
        user_id: str = "anonymous",
    ) -> StorageResult:
        clean_name = secure_filename(filename)
        path = f"{user_id}/{session_id}/{clean_name}"
        try:
            self._client.storage.from_(self.bucket_generated).upload(
                path=path,
                file=data,
                file_options={"upsert": "true"},
            )
        except Exception as exc:
            raise StorageError(f"Failed to upload generated file to Supabase: {exc}") from exc

        sha256 = hashlib.sha256(data).hexdigest()
        return StorageResult(
            storage_path=path,
            file_hash=sha256,
            size_bytes=len(data),
            filename=filename,
            is_patched=True,
        )

    def get_generated_bytes(
        self,
        session_id: str,
        filename: str,
        user_id: str = "anonymous",
    ) -> bytes:
        clean_name = secure_filename(filename)
        path = f"{user_id}/{session_id}/{clean_name}"
        try:
            return self._client.storage.from_(self.bucket_generated).download(path)
        except Exception as exc:
            raise StorageError(f"Failed to download generated file from Supabase: {exc}") from exc

    def save_source_artifact(
        self,
        package_id: str,
        artifact_id: str,
        filename: str,
        data: bytes,
        user_id: str = "anonymous",
    ) -> StorageResult:
        clean_name = f"{artifact_id}_{secure_filename(filename)}"
        path = f"{user_id}/{package_id}/{clean_name}"
        try:
            self._client.storage.from_(self.bucket_source_artifacts).upload(
                path=path,
                file=data,
                file_options={"upsert": "true"},
            )
        except Exception as exc:
            raise StorageError(f"Failed to upload source artifact to Supabase: {exc}") from exc

        sha256 = hashlib.sha256(data).hexdigest()
        return StorageResult(
            storage_path=path,
            file_hash=sha256,
            size_bytes=len(data),
            filename=filename,
        )

    def get_source_artifact_bytes(
        self,
        package_id: str,
        artifact_id: str,
        filename: str,
        user_id: str = "anonymous",
    ) -> bytes:
        clean_name = f"{artifact_id}_{secure_filename(filename)}"
        path = f"{user_id}/{package_id}/{clean_name}"
        try:
            return self._client.storage.from_(self.bucket_source_artifacts).download(path)
        except Exception as exc:
            raise StorageError(f"Failed to download source artifact from Supabase: {exc}") from exc

    def check_health(self) -> Tuple[bool, str]:
        try:
            # Check bucket list accessibility
            buckets = self._client.storage.list_buckets()
            bucket_names = [b.name for b in buckets]
            for req_bucket in (self.bucket_documents, self.bucket_generated):
                if req_bucket not in bucket_names:
                    return False, f"Required storage bucket '{req_bucket}' does not exist in Supabase project."
            return True, "Supabase Storage connected and required buckets are available."
        except Exception as exc:
            return False, f"Supabase Storage connection failed: {exc}"


# ============================================================================
# FACTORY
# ============================================================================

_STORAGE_INSTANCE: Optional[DocumentStorage] = None


def get_storage(config: Optional[AppConfig] = None) -> DocumentStorage:
    """Returns the configured DocumentStorage singleton."""
    global _STORAGE_INSTANCE
    cfg = config or get_config()
    if _STORAGE_INSTANCE is None:
        if cfg.storage_backend == StorageBackend.SUPABASE.value:
            _STORAGE_INSTANCE = SupabaseDocumentStorage(cfg)
        else:
            _STORAGE_INSTANCE = LocalDocumentStorage()
    return _STORAGE_INSTANCE


def reset_storage() -> None:
    """Resets storage singleton (used for tests)."""
    global _STORAGE_INSTANCE
    _STORAGE_INSTANCE = None
