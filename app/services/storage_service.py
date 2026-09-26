import re
import uuid
import shutil
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from app.config import settings

class StorageService:
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitizes filename to remove path traversal and risky characters."""
        # Strip path directory separators
        clean_name = Path(filename).name
        # Keep only alphanumeric, dots, underscores, dashes
        clean_name = re.sub(r"[^a-zA-Z0-9._-]", "_", clean_name)
        return clean_name or "uploaded_file"

    @classmethod
    async def validate_and_save_upload(cls, file: UploadFile) -> tuple[str, str]:
        """
        Validates the uploaded file for allowed extension and file size,
        saves it securely to the upload directory.
        Returns:
            (saved_file_path, sanitized_original_filename)
        """
        original_name = cls.sanitize_filename(file.filename or "unknown_file")
        ext = Path(original_name).suffix.lower()

        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type '{ext}'. Supported formats: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )

        # Generate unique storage filename to avoid collisions
        unique_name = f"{uuid.uuid4().hex[:8]}_{original_name}"
        dest_path = settings.UPLOAD_DIR / unique_name

        # Read in chunks to check size without loading massive files in memory
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        bytes_read = 0

        try:
            with open(dest_path, "wb") as buffer:
                while True:
                    chunk = await file.read(1024 * 1024)  # 1MB chunk
                    if not chunk:
                        break
                    bytes_read += len(chunk)
                    if bytes_read > max_bytes:
                        # Clean up partial file
                        buffer.close()
                        dest_path.unlink(missing_ok=True)
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB."
                        )
                    buffer.write(chunk)
        except HTTPException:
            raise
        except Exception as e:
            dest_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save uploaded file: {str(e)}"
            )
        finally:
            await file.seek(0)

        return str(dest_path), original_name
